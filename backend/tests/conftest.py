"""Test configuration.

Tests run against an isolated throwaway MongoDB database (`campus_delivery_test`
by default, or `TEST_MONGO_DB`/`TEST_MONGO_URL` if set). Every collection is
dropped and its indexes recreated before each test, so tests never touch
development or real data.
"""
import os

os.environ.setdefault("MONGO_URL", os.environ.get("TEST_MONGO_URL", "mongodb://localhost:27017"))
os.environ["MONGO_DB"] = os.environ.get("TEST_MONGO_DB", "campus_delivery_test")
os.environ["ENVIRONMENT"] = "test"
os.environ["SECRET_KEY"] = "test-only-secret-key-that-is-long-enough-123456"
os.environ["BCRYPT_ROUNDS"] = "4"
os.environ["NOTIFICATION_CHANNELS"] = "in_app"
os.environ["STORAGE_ALLOCATION_STRATEGY"] = "suitable_size"

from collections.abc import Iterator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.container import container  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.domain.enums import PackageSize, Role  # noqa: E402
from app.infrastructure.database import get_db, next_id, reset_db  # noqa: E402
from app.infrastructure.models import StorageLocation, User  # noqa: E402
from app.infrastructure.notifications import InAppChannel  # noqa: E402
from app.main import app  # noqa: E402

PASSWORD = "Passw0rd!"


@pytest.fixture(autouse=True)
def fresh_database() -> Iterator[None]:
    reset_db()
    container.login_limiter.reset()
    original_channels = container.dispatcher.channels
    container.dispatcher.channels = [InAppChannel()]
    yield
    container.dispatcher.channels = original_channels


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def users() -> dict[str, User]:
    specs = {
        "admin": ("ADM-001", "Ops Admin", Role.ADMIN),
        "sec1": ("SEC-001", "Guard One", Role.SECURITY),
        "sec2": ("SEC-002", "Guard Two", Role.SECURITY),
        "learner1": ("LRN-1001", "Learner One", Role.LEARNER),
        "learner2": ("LRN-1002", "Learner Two", Role.LEARNER),
    }
    created: dict[str, User] = {}
    db = get_db()
    for key, (inst, name, role) in specs.items():
        user = User(id=next_id(User.COLLECTION), institutional_id=inst, full_name=name,
                    email=f"{inst.lower()}@campus.example.edu", role=role,
                    password_hash=hash_password(PASSWORD), is_active=True)
        db[User.COLLECTION].insert_one(user.to_doc())
        created[key] = user
    return created


@pytest.fixture
def locations() -> dict[str, StorageLocation]:
    specs = {"small": ("T-S1", 2, PackageSize.SMALL), "medium": ("T-M1", 2, PackageSize.MEDIUM),
             "large": ("T-L1", 1, PackageSize.LARGE)}
    created: dict[str, StorageLocation] = {}
    db = get_db()
    for key, (code, cap, size) in specs.items():
        loc = StorageLocation(id=next_id(StorageLocation.COLLECTION), code=code, capacity=cap,
                              occupied_count=0, max_package_size=size, is_active=True)
        db[StorageLocation.COLLECTION].insert_one(loc.to_doc())
        created[key] = loc
    return created


def login(client: TestClient, institutional_id: str, password: str = PASSWORD) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"identifier": institutional_id, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def h(client: TestClient, users: dict[str, User]) -> dict[str, dict[str, str]]:
    """Auth headers for every demo user, keyed like the `users` fixture."""
    return {key: login(client, user.institutional_id) for key, user in users.items()}


def register(client: TestClient, headers: dict[str, str], **overrides) -> dict:
    body = {"courier_name": "BlueDart", "tracking_id": None, "recipient_institutional_id": "LRN-1001",
            "size": "SMALL", "condition": "GOOD"}
    body.update(overrides)
    response = client.post("/api/v1/packages", json=body, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def make_ready(client: TestClient, headers: dict[str, str], **overrides) -> dict:
    package = register(client, headers, **overrides)
    response = client.post(f"/api/v1/packages/{package['id']}/storage", json={"mark_ready": True}, headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "READY_FOR_PICKUP"
    return response.json()


def request_code(client: TestClient, learner_headers: dict[str, str], package_id: int) -> str:
    response = client.post(f"/api/v1/packages/{package_id}/pickup-request", headers=learner_headers)
    assert response.status_code == 201, response.text
    return response.json()["code"]
