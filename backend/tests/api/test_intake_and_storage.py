"""Package registration, validation, duplicates, unidentified/damaged workflows and storage."""
import threading

from app.container import container
from app.core.exceptions import AppError
from app.infrastructure.database import get_db
from app.infrastructure.models import Incident, Package, StorageLocation
from app.services.storage_allocation import StorageAllocationService
from tests.conftest import register


def test_register_and_store_package(client, h, locations):
    package = register(client, h["sec1"], tracking_id="bd 1234 5678")
    assert package["status"] == "VERIFIED"
    assert package["tracking_id"] == "BD12345678"
    assert package["received_by"]["institutional_id"] == "SEC-001"
    stored = client.post(f"/api/v1/packages/{package['id']}/storage", json={"location_id": locations["small"].id},
                         headers=h["sec1"]).json()
    assert stored["status"] == "STORED" and stored["storage_location"]["code"] == "T-S1"
    history = client.get(f"/api/v1/packages/{package['id']}/history", headers=h["sec1"]).json()
    assert [e["to_status"] for e in history] == ["RECEIVED", "VERIFIED", "STORED"]


def test_missing_and_malformed_fields_return_field_errors(client, h):
    response = client.post("/api/v1/packages", json={"size": "HUGE"}, headers=h["sec1"])
    assert response.status_code == 422
    fields = {e["field"] for e in response.json()["error"]["details"]}
    assert {"courier_name", "size"} <= fields
    damaged_without_notes = client.post("/api/v1/packages", json={
        "courier_name": "DTDC", "recipient_institutional_id": "LRN-1001", "condition": "DAMAGED"}, headers=h["sec1"])
    assert damaged_without_notes.status_code == 422
    no_recipient_info = client.post("/api/v1/packages", json={"courier_name": "DTDC"}, headers=h["sec1"])
    assert no_recipient_info.status_code == 422
    malformed = client.post("/api/v1/packages", content="{not json", headers={**h["sec1"],
                                                                                "Content-Type": "application/json"})
    assert malformed.status_code == 422


def test_duplicate_tracking_id_is_rejected_and_audited(client, h):
    first = register(client, h["sec1"], tracking_id="DUP-0001")
    response = client.post("/api/v1/packages", json={"courier_name": "DTDC", "tracking_id": "dup-0001",
                                                     "recipient_institutional_id": "LRN-1002"}, headers=h["sec2"])
    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "DUPLICATE_TRACKING_ID"
    assert error["details"]["existing_internal_code"] == first["internal_code"]
    audit = client.get("/api/v1/audit-logs?action=package.duplicate_rejected", headers=h["admin"]).json()
    assert audit["total"] == 1


def test_invalid_learner_id_is_rejected_with_guidance(client, h):
    response = client.post("/api/v1/packages", json={"courier_name": "DTDC", "recipient_institutional_id": "LRN-404"},
                           headers=h["sec1"])
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "LEARNER_NOT_FOUND"


def test_unidentified_package_enters_workflow_and_can_be_identified(client, h, locations):
    package = register(client, h["sec1"], recipient_institutional_id=None, recipient_hint="'A. One', Hostel C")
    assert package["status"] == "UNIDENTIFIED"
    client.post(f"/api/v1/packages/{package['id']}/storage", json={}, headers=h["sec1"])  # hold it on a shelf
    identified = client.post(f"/api/v1/packages/{package['id']}/recipient",
                             json={"learner_institutional_id": "LRN-1001"}, headers=h["sec1"]).json()
    assert identified["status"] == "STORED"
    assert identified["recipient"]["institutional_id"] == "LRN-1001"
    incident = get_db()[Incident.COLLECTION].find_one({"package_id": package["id"]})
    assert incident["status"] == "RESOLVED"


def test_damaged_package_is_held_and_incident_opened(client, h, locations):
    package = register(client, h["sec1"], condition="DAMAGED", condition_notes="Torn wrapping")
    assert package["status"] == "DAMAGED" and package["condition"] == "DAMAGED"
    incidents = client.get("/api/v1/incidents?type=DAMAGE", headers=h["admin"]).json()
    assert incidents["total"] == 1
    client.post(f"/api/v1/packages/{package['id']}/storage", json={}, headers=h["sec1"])
    released = client.post(f"/api/v1/packages/{package['id']}/transitions",
                           json={"target_status": "STORED", "reason": "Contents checked with learner"},
                           headers=h["sec1"]).json()
    assert released["status"] == "STORED"
    assert released["condition"] == "DAMAGED"  # physical condition is a fact, separate from status


def test_idempotent_registration_replays_instead_of_duplicating(client, h):
    body = {"courier_name": "DTDC", "recipient_institutional_id": "LRN-1001"}
    headers = {**h["sec1"], "Idempotency-Key": "retry-key-0001"}
    first = client.post("/api/v1/packages", json=body, headers=headers)
    second = client.post("/api/v1/packages", json=body, headers=headers)
    assert first.status_code == 201 and second.status_code == 200
    assert second.headers["Idempotent-Replayed"] == "true"
    assert first.json()["id"] == second.json()["id"]
    assert get_db()[Package.COLLECTION].count_documents({}) == 1
    different = client.post("/api/v1/packages", json={**body, "courier_name": "Ekart"}, headers=headers)
    assert different.status_code == 409 and different.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_full_location_rejects_additional_allocation(client, h, locations):
    a = register(client, h["sec1"], size="LARGE")
    b = register(client, h["sec1"], size="LARGE")
    large = locations["large"].id  # capacity 1
    assert client.post(f"/api/v1/packages/{a['id']}/storage", json={"location_id": large},
                       headers=h["sec1"]).status_code == 200
    response = client.post(f"/api/v1/packages/{b['id']}/storage", json={"location_id": large}, headers=h["sec1"])
    assert response.status_code == 409 and response.json()["error"]["code"] == "STORAGE_FULL"
    auto = client.post(f"/api/v1/packages/{b['id']}/storage", json={}, headers=h["sec1"])
    assert auto.status_code == 409  # no other location accepts LARGE
    assert client.get(f"/api/v1/packages/{b['id']}", headers=h["sec1"]).json()["status"] == "VERIFIED"


def test_unavailable_location_and_size_mismatch_are_rejected(client, h, locations):
    package = register(client, h["sec1"], size="MEDIUM")
    assert client.post(f"/api/v1/packages/{package['id']}/storage", json={"location_id": locations["small"].id},
                       headers=h["sec1"]).json()["error"]["code"] == "STORAGE_SIZE_MISMATCH"
    client.patch(f"/api/v1/storage-locations/{locations['medium'].id}", json={"is_active": False}, headers=h["admin"])
    response = client.post(f"/api/v1/packages/{package['id']}/storage",
                           json={"location_id": locations["medium"].id}, headers=h["sec1"])
    assert response.json()["error"]["code"] == "STORAGE_UNAVAILABLE"
    auto = client.post(f"/api/v1/packages/{package['id']}/storage", json={}, headers=h["sec1"]).json()
    assert auto["storage_location"]["code"] == "T-L1"  # strategy skips the inactive shelf


def test_capacity_cannot_drop_below_occupancy(client, h, locations):
    small = locations["small"].id  # capacity 2
    for _ in range(2):
        package = register(client, h["sec1"])
        client.post(f"/api/v1/packages/{package['id']}/storage", json={"location_id": small}, headers=h["sec1"])
    response = client.patch(f"/api/v1/storage-locations/{small}", json={"capacity": 1}, headers=h["admin"])
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CAPACITY_BELOW_OCCUPANCY"
    assert client.patch(f"/api/v1/storage-locations/{small}", json={"capacity": 5},
                        headers=h["admin"]).json()["capacity"] == 5


def test_moving_storage_releases_the_old_slot(client, h, locations):
    package = register(client, h["sec1"])
    client.post(f"/api/v1/packages/{package['id']}/storage", json={"location_id": locations["small"].id},
                headers=h["sec1"])
    client.post(f"/api/v1/packages/{package['id']}/storage", json={"location_id": locations["medium"].id},
                headers=h["sec1"])
    db = get_db()
    assert db[StorageLocation.COLLECTION].find_one({"_id": locations["small"].id})["occupied_count"] == 0
    assert db[StorageLocation.COLLECTION].find_one({"_id": locations["medium"].id})["occupied_count"] == 1


def test_concurrent_allocation_never_exceeds_capacity(client, h, users, locations):
    packages = [register(client, h["sec1"], size="LARGE") for _ in range(3)]
    barrier, outcomes = threading.Barrier(3), []

    def worker(package_id: int) -> None:
        barrier.wait()
        try:
            with container.uow() as uow:
                StorageAllocationService(uow, container.allocation_strategy).assign(
                    package_id=package_id, actor=uow.users.get(users["sec1"].id),
                    location_id=locations["large"].id)
            outcomes.append("ok")
        except AppError as error:
            outcomes.append(error.code)

    threads = [threading.Thread(target=worker, args=(p["id"],)) for p in packages]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sorted(outcomes) == ["STORAGE_FULL", "STORAGE_FULL", "ok"]
    assert get_db()[StorageLocation.COLLECTION].find_one({"_id": locations["large"].id})["occupied_count"] == 1
