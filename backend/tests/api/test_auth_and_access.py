"""Authentication, role-based access control and data isolation."""
from tests.conftest import PASSWORD, login, make_ready, register


def test_login_returns_token_and_profile(client, users):
    response = client.post("/api/v1/auth/login", json={"identifier": "lrn-1001", "password": PASSWORD})
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "LEARNER"
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {response.json()['access_token']}"})
    assert me.json()["institutional_id"] == "LRN-1001"


def test_login_by_email_works(client, users):
    response = client.post("/api/v1/auth/login", json={"identifier": "sec-001@campus.example.edu", "password": PASSWORD})
    assert response.status_code == 200


def test_wrong_password_is_rejected_without_detail(client, users):
    response = client.post("/api/v1/auth/login", json={"identifier": "LRN-1001", "password": "nope"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


def test_repeated_failed_logins_are_rate_limited(client, users):
    for _ in range(5):
        client.post("/api/v1/auth/login", json={"identifier": "LRN-1001", "password": "wrong"})
    response = client.post("/api/v1/auth/login", json={"identifier": "LRN-1001", "password": PASSWORD})
    assert response.status_code == 429


def test_requests_without_or_with_bad_token_are_rejected(client, users):
    assert client.get("/api/v1/packages").status_code == 401
    assert client.get("/api/v1/packages", headers={"Authorization": "Bearer junk"}).status_code == 401


def test_deactivated_user_loses_access_immediately(client, h, users):
    learner_headers = h["learner2"]
    response = client.patch(f"/api/v1/users/{users['learner2'].id}", json={"is_active": False}, headers=h["admin"])
    assert response.status_code == 200
    assert client.get("/api/v1/packages", headers=learner_headers).status_code == 401


def test_learner_sees_only_their_own_packages(client, h, locations):
    mine = register(client, h["sec1"], recipient_institutional_id="LRN-1001")
    theirs = register(client, h["sec1"], recipient_institutional_id="LRN-1002")
    listing = client.get("/api/v1/packages", headers=h["learner1"]).json()
    assert [p["id"] for p in listing["items"]] == [mine["id"]]
    # Direct access to another learner's package looks like it does not exist.
    assert client.get(f"/api/v1/packages/{theirs['id']}", headers=h["learner1"]).status_code == 404
    assert client.get(f"/api/v1/packages/{theirs['id']}/history", headers=h["learner1"]).status_code == 404


def test_learner_view_hides_staff_only_fields(client, h, locations):
    package = make_ready(client, h["sec1"], notes="fragile, keep upright")
    seen = client.get(f"/api/v1/packages/{package['id']}", headers=h["learner1"]).json()
    assert seen["received_by"] is None and seen["notes"] is None
    assert seen["storage_location"]["code"] == "T-S1"  # visible once ready for pickup
    history = client.get(f"/api/v1/packages/{package['id']}/history", headers=h["learner1"]).json()
    assert all(entry["changed_by"] is None for entry in history)


def test_learner_cannot_perform_staff_operations(client, h, locations):
    package = register(client, h["sec1"])
    assert client.post("/api/v1/packages", json={"courier_name": "X", "recipient_hint": "x"},
                       headers=h["learner1"]).status_code == 403
    assert client.post(f"/api/v1/packages/{package['id']}/storage", json={},
                       headers=h["learner1"]).status_code == 403
    assert client.get("/api/v1/reports/dashboard", headers=h["learner1"]).status_code == 403


def test_security_cannot_perform_admin_operations(client, h):
    new_user = {"institutional_id": "LRN-9", "full_name": "X Y", "email": "x@campus.example.edu", "role": "ADMIN",
                "password": "Secret123!"}
    assert client.post("/api/v1/users", json=new_user, headers=h["sec1"]).status_code == 403
    assert client.post("/api/v1/storage-locations", json={"code": "Z1", "capacity": 3},
                       headers=h["sec1"]).status_code == 403
    assert client.get("/api/v1/audit-logs", headers=h["sec1"]).status_code == 403
    assert client.get("/api/v1/audit-logs", headers=h["learner1"]).status_code == 403
    assert client.get("/api/v1/audit-logs", headers=h["admin"]).status_code == 200


def test_admin_manages_users(client, h):
    body = {"institutional_id": "SEC-777", "full_name": "Night Shift", "email": "night@campus.example.edu",
            "role": "SECURITY", "password": "NightShift1"}
    created = client.post("/api/v1/users", json=body, headers=h["admin"])
    assert created.status_code == 201
    assert client.post("/api/v1/users", json=body, headers=h["admin"]).status_code == 409
    login(client, "SEC-777", "NightShift1")


def test_security_can_search_learners(client, h):
    results = client.get("/api/v1/users/learners?q=learner two", headers=h["sec1"]).json()
    assert [r["institutional_id"] for r in results] == ["LRN-1002"]
    assert client.get("/api/v1/users/learners?q=lrn", headers=h["learner1"]).status_code == 403


def test_signup_creates_learner_and_signs_in(client):
    response = client.post("/api/v1/auth/signup", json={
        "institutional_id": "lrn-2001", "full_name": "New Learner", "email": "new.learner@campus.example.edu",
        "password": "NewLearner1"})
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["user"]["role"] == "LEARNER"
    assert body["user"]["institutional_id"] == "LRN-2001"
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.json()["email"] == "new.learner@campus.example.edu"


def test_signup_rejects_duplicate_id_or_email(client):
    payload = {"institutional_id": "LRN-2001", "full_name": "First", "email": "first@campus.example.edu",
               "password": "FirstPass1"}
    assert client.post("/api/v1/auth/signup", json=payload).status_code == 201
    assert client.post("/api/v1/auth/signup", json=payload).status_code == 409
    clash = {**payload, "institutional_id": "LRN-2002", "email": "first@campus.example.edu"}
    assert client.post("/api/v1/auth/signup", json=clash).status_code == 409


def test_signup_enforces_password_strength(client):
    response = client.post("/api/v1/auth/signup", json={
        "institutional_id": "lrn-2003", "full_name": "Weak Pass", "email": "weak@campus.example.edu",
        "password": "passwordonly"})
    assert response.status_code == 422
