"""Learner-initiated return of a package to the courier."""
from tests.conftest import make_ready

from app.infrastructure.database import get_db
from app.infrastructure.models import StorageLocation


def test_learner_requests_return_of_own_package(client, h, locations):
    package = make_ready(client, h["sec1"])
    response = client.post(f"/api/v1/packages/{package['id']}/return-request",
                           json={"reason": "I no longer need it"}, headers=h["learner1"])
    assert response.status_code == 201, response.text
    assert response.json()["status"] == "RETURN_REQUESTED"


def test_learner_cannot_return_another_learners_package(client, h, locations):
    package = make_ready(client, h["sec1"], recipient_institutional_id="LRN-1002")
    response = client.post(f"/api/v1/packages/{package['id']}/return-request",
                           json={"reason": "not mine"}, headers=h["learner1"])
    assert response.status_code == 404


def test_return_request_requires_a_reason(client, h, locations):
    package = make_ready(client, h["sec1"])
    assert client.post(f"/api/v1/packages/{package['id']}/return-request", json={},
                       headers=h["learner1"]).status_code == 422
    assert client.post(f"/api/v1/packages/{package['id']}/return-request", json={"reason": "x"},
                       headers=h["learner1"]).status_code == 422


def test_collected_package_cannot_be_returned(client, h, locations):
    package = make_ready(client, h["sec1"])
    code = client.post(f"/api/v1/packages/{package['id']}/pickup-request", headers=h["learner1"]).json()["code"]
    client.post("/api/v1/pickups/complete", json={
        "package_code": package["internal_code"], "learner_institutional_id": "LRN-1001", "code": code},
        headers=h["sec1"])
    response = client.post(f"/api/v1/packages/{package['id']}/return-request",
                           json={"reason": "changed my mind"}, headers=h["learner1"])
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"


def test_staff_handing_package_back_frees_the_shelf(client, h, locations):
    package = make_ready(client, h["sec1"])
    client.post(f"/api/v1/packages/{package['id']}/return-request", json={"reason": "sent it back"},
                headers=h["learner1"])
    response = client.post(f"/api/v1/packages/{package['id']}/transitions",
                           json={"target_status": "RETURNED", "reason": "courier picked it up"}, headers=h["sec1"])
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "RETURNED"
    assert get_db()[StorageLocation.COLLECTION].find_one({"_id": locations["small"].id})["occupied_count"] == 0
