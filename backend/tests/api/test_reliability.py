"""Transaction atomicity, notification failure, overdue, returns, incidents and reporting."""
from datetime import timedelta

from fastapi.testclient import TestClient

from app.container import container
from app.core.exceptions import NotificationDeliveryError
from app.core.time import utcnow
from app.domain.enums import NotificationChannelType
from app.infrastructure.database import get_db
from app.infrastructure.models import AuditLog, Notification, Package, PickupRecord, StorageLocation
from app.infrastructure.notifications import InAppChannel
from app.main import app
from app.repositories.mongo_repos import MongoPickupRecordRepository
from tests.conftest import make_ready, register, request_code


class BrokenEmail:
    channel_type = NotificationChannelType.EMAIL

    def send(self, recipient, title, message):  # noqa: ANN001
        raise NotificationDeliveryError("SMTP server unreachable")


class WorkingEmail:
    channel_type = NotificationChannelType.EMAIL

    def send(self, recipient, title, message):  # noqa: ANN001
        return None


def test_failure_halfway_through_handover_rolls_everything_back(h, locations, monkeypatch):
    client = TestClient(app, raise_server_exceptions=False)
    package = make_ready(client, h["sec1"])
    code = request_code(client, h["learner1"], package["id"])

    def explode(self, record):  # noqa: ANN001
        raise RuntimeError("disk full while writing pickup record")

    monkeypatch.setattr(MongoPickupRecordRepository, "add", explode)
    response = client.post("/api/v1/pickups/complete", headers=h["sec1"], json={
        "package_code": package["internal_code"], "learner_institutional_id": "LRN-1001", "code": code})
    assert response.status_code == 500
    assert "disk full" not in response.text  # no internal details leak
    assert response.json()["error"]["request_id"]
    # Standalone MongoDB has no multi-document transaction, so writes made earlier
    # in the use case are already persisted. The failed write must still leave no
    # pickup record and no matching audit entry behind.
    db = get_db()
    assert db[PickupRecord.COLLECTION].count_documents({}) == 0
    assert db[AuditLog.COLLECTION].count_documents({"action": "pickup.completed"}) == 0


def test_notification_failure_does_not_undo_the_package_update(client, h, locations):
    container.dispatcher.channels = [InAppChannel(), BrokenEmail()]
    package = make_ready(client, h["sec1"])  # succeeds even though email fails
    assert package["status"] == "READY_FOR_PICKUP"
    db = get_db()
    email = db[Notification.COLLECTION].find_one({"channel": "EMAIL", "title": "Ready for pickup"})
    in_app = db[Notification.COLLECTION].find_one({"channel": "IN_APP", "title": "Ready for pickup"})
    assert email["delivery_status"] == "FAILED" and "SMTP" in email["last_error"]
    assert in_app["delivery_status"] == "SENT"

    dashboard = client.get("/api/v1/reports/dashboard", headers=h["admin"]).json()
    assert dashboard["failed_notifications"] == 2  # arrival + ready emails

    container.dispatcher.channels = [InAppChannel(), WorkingEmail()]
    result = client.post("/api/v1/notifications/retry-failed", headers=h["admin"]).json()
    assert result == {"retried": 2, "sent": 2, "failed": 0, "skipped": 0}


def test_learner_notifications_can_be_marked_read(client, h, locations):
    make_ready(client, h["sec1"])
    assert client.get("/api/v1/notifications/unread-count", headers=h["learner1"]).json()["unread"] == 2
    items = client.get("/api/v1/notifications", headers=h["learner1"]).json()["items"]
    assert client.post(f"/api/v1/notifications/{items[0]['id']}/read", headers=h["learner2"]).status_code == 404
    client.post(f"/api/v1/notifications/{items[0]['id']}/read", headers=h["learner1"])
    assert client.get("/api/v1/notifications/unread-count", headers=h["learner1"]).json()["unread"] == 1
    client.post("/api/v1/notifications/read-all", headers=h["learner1"])
    assert client.get("/api/v1/notifications/unread-count", headers=h["learner1"]).json()["unread"] == 0


def test_overdue_packages_are_flagged_and_filterable(client, h, locations):
    late = make_ready(client, h["sec1"])
    make_ready(client, h["sec1"])
    db = get_db()
    db[Package.COLLECTION].update_one({"_id": late["id"]},
                                      {"$set": {"arrived_at": utcnow() - timedelta(days=9)}})
    overdue = client.get("/api/v1/packages?overdue=true", headers=h["admin"]).json()
    assert [p["id"] for p in overdue["items"]] == [late["id"]]
    assert overdue["items"][0]["is_overdue"] is True
    assert overdue["items"][0]["status"] == "READY_FOR_PICKUP"  # still collectable
    assert client.get("/api/v1/reports/dashboard", headers=h["admin"]).json()["overdue"] == 1


def test_return_to_courier_flow_releases_storage(client, h, locations):
    package = make_ready(client, h["sec1"])
    no_reason = client.post(f"/api/v1/packages/{package['id']}/transitions",
                            json={"target_status": "RETURN_REQUESTED"}, headers=h["admin"])
    assert no_reason.json()["error"]["code"] == "REASON_REQUIRED"
    security_denied = client.post(f"/api/v1/packages/{package['id']}/transitions",
                                  json={"target_status": "RETURN_REQUESTED", "reason": "Uncollected"},
                                  headers=h["sec1"])
    assert security_denied.status_code == 403
    requested = client.post(f"/api/v1/packages/{package['id']}/transitions",
                            json={"target_status": "RETURN_REQUESTED", "reason": "Uncollected after deadline"},
                            headers=h["admin"])
    assert requested.json()["status"] == "RETURN_REQUESTED"
    returned = client.post(f"/api/v1/packages/{package['id']}/transitions",
                           json={"target_status": "RETURNED", "reason": "Courier collected"}, headers=h["sec1"])
    assert returned.json()["status"] == "RETURNED"
    db = get_db()
    assert db[StorageLocation.COLLECTION].find_one({"_id": locations["small"].id})["occupied_count"] == 0


def test_dedicated_transitions_cannot_be_forced_through_generic_endpoint(client, h, locations):
    package = make_ready(client, h["sec1"])
    client.post(f"/api/v1/packages/{package['id']}/pickup-request", headers=h["learner1"])
    response = client.post(f"/api/v1/packages/{package['id']}/transitions",
                           json={"target_status": "COLLECTED"}, headers=h["sec1"])
    assert response.json()["error"]["code"] == "USE_DEDICATED_ENDPOINT"


def test_incidents_escalate_and_resolve(client, h, locations):
    package = make_ready(client, h["sec1"])
    learner_issue = client.post("/api/v1/incidents", json={"package_id": package["id"], "type": "OPERATIONAL",
                                                           "description": "Label shows wrong hostel",
                                                           "escalate": True}, headers=h["learner1"]).json()
    assert learner_issue["type"] == "LEARNER_REPORTED_ISSUE"  # learners cannot escalate or pick types
    assert client.post("/api/v1/incidents", json={"package_id": package["id"], "description": "not mine at all"},
                       headers=h["learner2"]).status_code == 404
    staff = client.post("/api/v1/incidents", json={"package_id": package["id"], "type": "MISSING_PACKAGE",
                                                   "description": "Not on shelf at shift change", "escalate": True},
                        headers=h["sec2"]).json()
    assert client.get(f"/api/v1/packages/{package['id']}", headers=h["sec1"]).json()["status"] == "UNDER_INVESTIGATION"
    assert client.post(f"/api/v1/incidents/{staff['id']}/resolve", json={"resolution_note": "Found"},
                       headers=h["sec1"]).status_code == 403
    resolved = client.post(f"/api/v1/incidents/{staff['id']}/resolve", json={"resolution_note": "Found on M1"},
                           headers=h["admin"]).json()
    assert resolved["status"] == "RESOLVED" and resolved["resolved_by"]["institutional_id"] == "ADM-001"
    mine = client.get("/api/v1/incidents", headers=h["learner1"]).json()
    assert [i["id"] for i in mine["items"]] == [learner_issue["id"]]


def test_dashboard_and_daily_report_reflect_database(client, h, locations):
    register(client, h["sec1"], recipient_institutional_id=None, recipient_hint="unknown")
    register(client, h["sec1"], condition="DAMAGED", condition_notes="wet")
    package = make_ready(client, h["sec1"])
    code = request_code(client, h["learner1"], package["id"])
    client.post("/api/v1/pickups/complete", headers=h["sec1"], json={
        "package_code": package["internal_code"], "learner_institutional_id": "LRN-1001", "code": code})
    stats = client.get("/api/v1/reports/dashboard", headers=h["admin"]).json()
    assert stats["received"] == 3 and stats["received_today"] == 3 and stats["collected_today"] == 1
    assert stats["by_status"]["UNIDENTIFIED"] == 1 and stats["by_status"]["DAMAGED"] == 1
    assert stats["by_status"]["COLLECTED"] == 1 and stats["open_incidents"] == 2
    rows = client.get("/api/v1/reports/daily", headers=h["admin"]).json()
    assert rows[-1]["received"] == 3 and rows[-1]["collected"] == 1 and len(rows) == 14
    assert client.get("/api/v1/reports/daily", headers=h["sec1"]).status_code == 403


def test_search_filter_and_pagination(client, h, locations):
    for i in range(5):
        register(client, h["sec1"], tracking_id=f"PAGE-{i:04d}")
    page = client.get("/api/v1/packages?page=2&page_size=2", headers=h["sec1"]).json()
    assert page["total"] == 5 and len(page["items"]) == 2
    found = client.get("/api/v1/packages?q=page-0003", headers=h["sec1"]).json()
    assert found["total"] == 1
    by_name = client.get("/api/v1/packages?q=learner one&status=VERIFIED", headers=h["sec1"]).json()
    assert by_name["total"] == 5
