"""Development-only demo data. Run: `python -m app.seed`

All credentials below are LOCAL TESTING CREDENTIALS for a fictional campus.
No real learner data is used. The script refuses to run in production and is
safe to run twice (it skips seeding when users already exist).

Packages are created through the real services, so status history, audit
logs and notifications are genuine.
"""
from datetime import timedelta

from app.container import container
from app.core.config import get_settings
from app.core.security import hash_password
from app.core.time import utcnow
from app.domain.enums import IncidentType, PackageCondition, PackageSize, Role
from app.infrastructure.database import get_db, init_db, next_id
from app.infrastructure.models import Package, PickupRecord, StorageLocation, User
from app.services.incidents import IncidentService
from app.services.package_intake import PackageIntakeService
from app.services.pickup import PickupService
from app.services.storage_allocation import StorageAllocationService

DEMO_PASSWORD_NOTE = "LOCAL TESTING CREDENTIALS ONLY"

USERS = [
    ("ADM-001", "Priya Raman", "ops.admin@campus.example.edu", Role.ADMIN, "Admin@12345"),
    ("SEC-001", "Arjun Mehta", "arjun.security@campus.example.edu", Role.SECURITY, "Security@123"),
    ("SEC-002", "Kavya Nair", "kavya.security@campus.example.edu", Role.SECURITY, "Security@123"),
    ("LRN-1001", "Ananya Iyer", "ananya@learners.example.edu", Role.LEARNER, "Learner@123"),
    ("LRN-1002", "Rohan Das", "rohan@learners.example.edu", Role.LEARNER, "Learner@123"),
    ("LRN-1003", "Meera Joshi", "meera@learners.example.edu", Role.LEARNER, "Learner@123"),
    ("LRN-1004", "Vikram Singh", "vikram@learners.example.edu", Role.LEARNER, "Learner@123"),
    ("230136", "Kalash Kumari", "230136@learners.example.edu", Role.LEARNER, "Learner@123"),
]

LOCATIONS = [
    ("G2-S1", "Gate 2 shelf 1 (envelopes, small boxes)", 12, PackageSize.SMALL),
    ("G2-S2", "Gate 2 shelf 2 (envelopes, small boxes)", 12, PackageSize.SMALL),
    ("G2-M1", "Gate 2 rack, medium boxes", 8, PackageSize.MEDIUM),
    ("G2-M2", "Gate 2 rack, medium boxes", 8, PackageSize.MEDIUM),
    ("G2-L1", "Gate 2 floor bay, large parcels", 4, PackageSize.LARGE),
    ("G2-X1", "Overflow cage (closed for repair)", 6, PackageSize.LARGE),
]


def ensure_demo_users() -> None:
    """Ensure the local testing accounts exist with their correct passwords and are active.
    
    Safe to call on application startup or repeatedly in development.
    """
    settings = get_settings()
    if settings.environment == "production":
        return
    init_db()
    db = get_db()

    for inst_id, name, email, role, password in USERS:
        existing = db[User.COLLECTION].find_one({
            "$or": [{"institutional_id": inst_id}, {"email": email}]
        })
        hashed = hash_password(password)
        if existing:
            db[User.COLLECTION].update_one(
                {"_id": existing["_id"]},
                {"$set": {
                    "institutional_id": inst_id,
                    "password_hash": hashed,
                    "is_active": True,
                    "role": role.value,
                    "email": email,
                    "full_name": name,
                }}
            )
        else:
            db[User.COLLECTION].insert_one(User(
                id=next_id(User.COLLECTION), institutional_id=inst_id, full_name=name, email=email,
                role=role, password_hash=hashed, is_active=True).to_doc())

    for code, desc, cap, size in LOCATIONS:
        if db[StorageLocation.COLLECTION].find_one({"code": code}) is None:
            db[StorageLocation.COLLECTION].insert_one(StorageLocation(
                id=next_id(StorageLocation.COLLECTION), code=code, description=desc, capacity=cap,
                max_package_size=size, occupied_count=0, is_active=code != "G2-X1").to_doc())

    try:
        container.login_limiter.reset()
    except Exception:
        pass


def seed() -> None:
    import sys
    settings = get_settings()
    if settings.environment == "production":
        raise SystemExit("Refusing to seed demo data in production.")
    
    force_reset = "--reset" in sys.argv or "--force" in sys.argv
    db = get_db()

    if force_reset:
        print("Resetting database before seeding...")
        from app.infrastructure.database import reset_db
        reset_db()

    ensure_demo_users()

    if not force_reset and db[Package.COLLECTION].find_one({}, {"_id": 1}) is not None:
        print("Testing accounts updated. Packages already exist; skipping package seed.")
        for inst_id, name, _, role, password in USERS:
            print(f"  {role.value:<8} {inst_id:<9} {password:<13} {name}")
        return

    def user(inst_id: str) -> User:
        doc = db[User.COLLECTION].find_one({"institutional_id": inst_id})
        return User.from_doc(doc)

    sec1, sec2 = user("SEC-001"), user("SEC-002")
    now = utcnow()

    def register(actor: User, courier: str, tracking: str | None, learner: str | None, **kw) -> Package:
        with container.uow() as uow:
            pkg, _ = PackageIntakeService(uow).register(
                actor=actor, courier_name=courier, tracking_id=tracking, recipient_institutional_id=learner,
                recipient_hint=kw.get("hint"), size=kw.get("size", PackageSize.SMALL),
                condition=kw.get("condition", PackageCondition.GOOD), condition_notes=kw.get("notes"),
                arrived_at=kw.get("arrived_at", now), notes=None)
            return pkg

    def store(actor: User, pkg: Package, ready: bool) -> None:
        with container.uow() as uow:
            StorageAllocationService(uow, container.allocation_strategy).assign(
                package_id=pkg.id, actor=actor, location_id=None, mark_ready=ready)

    # 1. Ready for pickup (Ananya / LRN-1001) -> Click "Request Pickup Code" to test generation
    p1 = register(sec1, "BlueDart", "BD7781200345", "LRN-1001", arrived_at=now - timedelta(hours=3))
    store(sec1, p1, ready=True)

    # 2. Active pickup code already generated (Ananya / LRN-1001) -> Shows active token screen
    p_code = register(sec1, "Flipkart", "FMPC-88991200", "LRN-1001", size=PackageSize.SMALL,
                      arrived_at=now - timedelta(hours=2))
    store(sec1, p_code, ready=True)
    with container.uow() as uow:
        PickupService(uow, settings).request_pickup(package_id=p_code.id, learner=user("LRN-1001"))

    # 3. Stored, not yet marked ready (Ananya / LRN-1001)
    p2 = register(sec1, "Amazon Logistics", "AMZ-IN-55012", "LRN-1001", size=PackageSize.MEDIUM,
                  arrived_at=now - timedelta(hours=1))
    store(sec1, p2, ready=False)

    # 4. Overdue: arrived 8 days ago, still waiting (Rohan / LRN-1002)
    p3 = register(sec2, "DTDC", "DT90011223", "LRN-1002", size=PackageSize.MEDIUM,
                  arrived_at=now - timedelta(days=8))
    store(sec2, p3, ready=True)

    # 5. Verified student match, awaiting storage assignment (Meera / LRN-1003)
    register(sec2, "India Post", "EE123456789IN", "LRN-1003")

    # 6. Unidentified recipient (no student ID on label) -> Test manual match
    register(sec1, "Delhivery", "DLV0099887766", None, hint="'R. Kumar, Hostel B' (no learner ID)",
             size=PackageSize.SMALL, arrived_at=now - timedelta(days=2))

    # 7. Damaged on arrival with open incident (Vikram / LRN-1004) -> Test Ops Admin incident resolution
    p6 = register(sec2, "Ekart", "EK44551230", "LRN-1004", size=PackageSize.LARGE, condition=PackageCondition.DAMAGED,
                  notes="Box corner crushed, contents rattle", arrived_at=now - timedelta(hours=5))
    with container.uow() as uow:
        IncidentService(uow).report(
            actor=sec2, package_id=p6.id, kind=IncidentType.DAMAGE,
            description="Outer box crushed upon delivery from Ekart. Fragile contents suspected broken. Needs admin review.")
    # Collected yesterday (Rohan) via the full pickup flow, handed over by a different shift
    p7 = register(sec1, "BlueDart", "BD7781200999", "LRN-1002", arrived_at=now - timedelta(days=1, hours=4))
    store(sec1, p7, ready=True)
    with container.uow() as uow:
        issued = PickupService(uow, settings).request_pickup(package_id=p7.id, learner=user("LRN-1002"))
    with container.uow() as uow:
        PickupService(uow, settings).complete(package_code=p7.internal_code, learner_institutional_id="LRN-1002",
                                              code=issued.code, actor=sec2)

    # Spread demo arrivals over the last fortnight so the daily report has shape.
    for i in range(10):
        p = register(sec1 if i % 2 else sec2, "Amazon Logistics", f"AMZ-HIST-{i:04d}", "LRN-1003",
                     arrived_at=now - timedelta(days=13 - i, hours=2))
        store(sec1, p, ready=True)
        with container.uow() as uow:
            issued = PickupService(uow, settings).request_pickup(package_id=p.id, learner=user("LRN-1003"))
        with container.uow() as uow:
            record, _ = PickupService(uow, settings).complete(
                package_code=p.internal_code, learner_institutional_id="LRN-1003", code=issued.code, actor=sec1)
        # Backdate the handover to the day after arrival.
        when = now - timedelta(days=12 - i)
        db[PickupRecord.COLLECTION].update_one({"_id": record.id}, {"$set": {"collected_at": when}})
        db[Package.COLLECTION].update_one({"_id": p.id}, {"$set": {"closed_at": when}})

    print("Seed complete.", DEMO_PASSWORD_NOTE)
    for inst_id, name, _, role, password in USERS:
        print(f"  {role.value:<8} {inst_id:<9} {password:<13} {name}")


if __name__ == "__main__":
    seed()
