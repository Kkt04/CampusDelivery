"""Pickup code issuance, verification, handover, and double-collection protection."""
import threading

from app.container import container
from app.core.exceptions import AppError
from app.core.time import utcnow
from app.infrastructure.database import get_db
from app.infrastructure.models import Package, PickupRecord, PickupToken, StorageLocation
from app.services.pickup import PickupService
from tests.conftest import make_ready, register, request_code


def handover_body(package: dict, code: str, learner: str = "LRN-1001") -> dict:
    return {"package_code": package["internal_code"], "learner_institutional_id": learner, "code": code}


def test_full_pickup_flow_releases_storage_and_notifies(client, h, locations):
    package = make_ready(client, h["sec1"])
    code = request_code(client, h["learner1"], package["id"])
    assert client.get(f"/api/v1/packages/{package['id']}", headers=h["learner1"]).json()["status"] == "PICKUP_REQUESTED"

    verified = client.post("/api/v1/pickups/verify", json=handover_body(package, code), headers=h["sec1"])
    assert verified.status_code == 200 and verified.json()["verified"] is True

    done = client.post("/api/v1/pickups/complete", json=handover_body(package, code), headers=h["sec1"])
    assert done.status_code == 201
    assert done.json()["handed_over_by"]["institutional_id"] == "SEC-001"
    final = client.get(f"/api/v1/packages/{package['id']}", headers=h["sec1"]).json()
    assert final["status"] == "COLLECTED" and final["storage_location"] is None and final["closed_at"]
    db = get_db()
    assert db[StorageLocation.COLLECTION].find_one({"_id": locations["small"].id})["occupied_count"] == 0
    titles = [n["title"] for n in client.get("/api/v1/notifications", headers=h["learner1"]).json()["items"]]
    assert titles[:3] == ["Package collected", "Ready for pickup", "Package arrived"]
    history = client.get("/api/v1/pickups", headers=h["learner1"]).json()
    assert history["total"] == 1 and history["items"][0]["handed_over_by"] is None  # staff hidden from learner


def test_pickup_cannot_be_requested_before_ready(client, h, locations):
    package = register(client, h["sec1"])
    response = client.post(f"/api/v1/packages/{package['id']}/pickup-request", headers=h["learner1"])
    assert response.status_code == 409 and response.json()["error"]["code"] == "PICKUP_NOT_AVAILABLE"


def test_learner_cannot_request_pickup_for_someone_elses_package(client, h, locations):
    package = make_ready(client, h["sec1"])
    assert client.post(f"/api/v1/packages/{package['id']}/pickup-request", headers=h["learner2"]).status_code == 404


def test_wrong_code_and_wrong_learner_are_rejected_and_counted(client, h, locations):
    package = make_ready(client, h["sec1"])
    code = request_code(client, h["learner1"], package["id"])
    wrong = "000000" if code != "000000" else "111111"
    r1 = client.post("/api/v1/pickups/complete", json=handover_body(package, wrong), headers=h["sec1"])
    assert r1.json()["error"]["code"] == "PICKUP_CODE_INVALID"
    r2 = client.post("/api/v1/pickups/complete", json=handover_body(package, code, learner="LRN-1002"),
                     headers=h["sec1"])
    assert r2.json()["error"]["code"] == "PICKUP_WRONG_RECIPIENT"
    token = get_db()[PickupToken.COLLECTION].find_one({"package_id": package["id"]})
    assert token["failed_attempts"] == 2 and token["used_at"] is None


def test_code_locks_after_too_many_wrong_attempts(client, h, locations):
    package = make_ready(client, h["sec1"])
    code = request_code(client, h["learner1"], package["id"])
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(container.settings.pickup_code_max_attempts):
        client.post("/api/v1/pickups/verify", json=handover_body(package, wrong), headers=h["sec1"])
    response = client.post("/api/v1/pickups/complete", json=handover_body(package, code), headers=h["sec1"])
    assert response.json()["error"]["code"] == "PICKUP_CODE_LOCKED"


def test_expired_code_is_rejected_and_a_new_code_works(client, h, locations):
    package = make_ready(client, h["sec1"])
    old_code = request_code(client, h["learner1"], package["id"])
    get_db()[PickupToken.COLLECTION].update_many({}, {"$set": {"expires_at": utcnow()}})
    response = client.post("/api/v1/pickups/complete", json=handover_body(package, old_code), headers=h["sec1"])
    assert response.json()["error"]["code"] == "PICKUP_CODE_EXPIRED"
    new_code = request_code(client, h["learner1"], package["id"])  # learner simply asks again
    assert client.post("/api/v1/pickups/complete", json=handover_body(package, new_code),
                       headers=h["sec1"]).status_code == 201


def test_requesting_again_revokes_the_previous_code(client, h, locations):
    package = make_ready(client, h["sec1"])
    first = request_code(client, h["learner1"], package["id"])
    second = request_code(client, h["learner1"], package["id"])
    if first != second:
        stale = client.post("/api/v1/pickups/complete", json=handover_body(package, first), headers=h["sec1"])
        assert stale.json()["error"]["code"] == "PICKUP_CODE_INVALID"
    assert client.post("/api/v1/pickups/complete", json=handover_body(package, second),
                       headers=h["sec1"]).status_code == 201


def test_reused_code_and_already_collected_package_are_rejected(client, h, locations):
    package = make_ready(client, h["sec1"])
    code = request_code(client, h["learner1"], package["id"])
    assert client.post("/api/v1/pickups/complete", json=handover_body(package, code),
                       headers=h["sec1"]).status_code == 201
    again = client.post("/api/v1/pickups/complete", json=handover_body(package, code), headers=h["sec2"])
    assert again.status_code == 409 and again.json()["error"]["code"] == "ALREADY_COLLECTED"
    request_again = client.post(f"/api/v1/packages/{package['id']}/pickup-request", headers=h["learner1"])
    assert request_again.json()["error"]["code"] == "ALREADY_COLLECTED"
    back_to_ready = client.post(f"/api/v1/packages/{package['id']}/transitions",
                                json={"target_status": "READY_FOR_PICKUP"}, headers=h["admin"])
    assert back_to_ready.status_code == 409


def test_network_retry_of_handover_is_replayed(client, h, locations):
    package = make_ready(client, h["sec1"])
    code = request_code(client, h["learner1"], package["id"])
    headers = {**h["sec1"], "Idempotency-Key": "handover-retry-1"}
    first = client.post("/api/v1/pickups/complete", json=handover_body(package, code), headers=headers)
    retry = client.post("/api/v1/pickups/complete", json=handover_body(package, code), headers=headers)
    assert first.status_code == 201 and retry.status_code == 200
    assert retry.json()["id"] == first.json()["id"]
    assert get_db()[PickupRecord.COLLECTION].count_documents({}) == 1


def test_shift_change_does_not_block_the_workflow(client, h, locations):
    """Package registered by one guard is handed over by another; both are recorded."""
    package = make_ready(client, h["sec1"])
    code = request_code(client, h["learner1"], package["id"])
    record = client.post("/api/v1/pickups/complete", json=handover_body(package, code), headers=h["sec2"]).json()
    assert record["handed_over_by"]["institutional_id"] == "SEC-002"
    detail = client.get(f"/api/v1/packages/{package['id']}", headers=h["admin"]).json()
    assert detail["received_by"]["institutional_id"] == "SEC-001"


def test_concurrent_handover_results_in_exactly_one_collection(client, h, users, locations):
    package = make_ready(client, h["sec1"])
    code = request_code(client, h["learner1"], package["id"])
    barrier, outcomes = threading.Barrier(2), []

    def worker(staff_id: int) -> None:
        barrier.wait()
        try:
            with container.uow() as uow:
                PickupService(uow, container.settings).complete(
                    package_code=package["internal_code"], learner_institutional_id="LRN-1001", code=code,
                    actor=uow.users.get(staff_id))
            outcomes.append("ok")
        except AppError as error:
            outcomes.append(error.code)

    threads = [threading.Thread(target=worker, args=(users[k].id,)) for k in ("sec1", "sec2")]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sorted(outcomes) == ["ALREADY_COLLECTED", "ok"]
    db = get_db()
    assert db[PickupRecord.COLLECTION].count_documents({"package_id": package["id"]}) == 1
    assert db[Package.COLLECTION].find_one({"_id": package["id"]})["status"] == "COLLECTED"
    assert db[StorageLocation.COLLECTION].find_one({"_id": locations["small"].id})["occupied_count"] == 0
