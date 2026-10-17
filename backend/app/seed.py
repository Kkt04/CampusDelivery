"""Development-only demo data. Run: `python -m app.seed`

All credentials below are LOCAL TESTING CREDENTIALS for a fictional campus.
No real learner data is used. The script refuses to run in production and is
safe to run twice (it skips seeding when users already exist).

Packages are created through the real services, so status history, audit
logs and notifications are genuine.
"""
from datetime import timedelta

from sqlalchemy import select, update

from app.container import container
from app.core.config import get_settings
from app.core.security import hash_password
from app.core.time import utcnow
from app.domain.enums import PackageCondition, PackageSize, Role
from app.infrastructure.models import Package, PickupRecord, StorageLocation, User
from app.services.pickup import PickupService
from app.services.package_intake import PackageIntakeService
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
]

LOCATIONS = [
    ("G2-S1", "Gate 2 shelf 1 (envelopes, small boxes)", 12, PackageSize.SMALL),
    ("G2-S2", "Gate 2 shelf 2 (envelopes, small boxes)", 12, PackageSize.SMALL),
    ("G2-M1", "Gate 2 rack, medium boxes", 8, PackageSize.MEDIUM),
    ("G2-M2", "Gate 2 rack, medium boxes", 8, PackageSize.MEDIUM),
    ("G2-L1", "Gate 2 floor bay, large parcels", 4, PackageSize.LARGE),
    ("G2-X1", "Overflow cage (closed for repair)", 6, PackageSize.LARGE),
]


def seed() -> None:
    settings = get_settings()
    if settings.environment == "production":
        raise SystemExit("Refusing to seed demo data in production.")

    with container.session_factory() as session:
        if session.scalar(select(User.id).limit(1)) is not None:
            print("Users already exist; skipping seed.")
            return
        for inst_id, name, email, role, password in USERS:
            session.add(User(institutional_id=inst_id, full_name=name, email=email, role=role,
                             password_hash=hash_password(password), is_active=True))
        for code, desc, cap, size in LOCATIONS:
            session.add(StorageLocation(code=code, description=desc, capacity=cap, max_package_size=size,
                                        occupied_count=0, is_active=code != "G2-X1"))
        session.commit()

    def user(inst_id: str) -> User:
        with container.session_factory() as s:
            return s.scalar(select(User).where(User.institutional_id == inst_id))

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

    # Ready for pickup (Ananya)
    p1 = register(sec1, "BlueDart", "BD7781200345", "LRN-1001", arrived_at=now - timedelta(hours=3))
    store(sec1, p1, ready=True)
    # Stored, not yet marked ready (Ananya)
    p2 = register(sec1, "Amazon Logistics", "AMZ-IN-55012", "LRN-1001", size=PackageSize.MEDIUM,
                  arrived_at=now - timedelta(hours=1))
    store(sec1, p2, ready=False)
    # Overdue: arrived 8 days ago, still waiting (Rohan)
    p3 = register(sec2, "DTDC", "DT90011223", "LRN-1002", size=PackageSize.MEDIUM,
                  arrived_at=now - timedelta(days=8))
    store(sec2, p3, ready=True)
    # Verified, awaiting storage (Meera)
    register(sec2, "India Post", "EE123456789IN", "LRN-1003")
    # Unidentified recipient
    register(sec1, "Delhivery", "DLV0099887766", None, hint="'R. Kumar, Hostel B' (no learner ID)",
             size=PackageSize.SMALL, arrived_at=now - timedelta(days=2))
    # Damaged on arrival (Vikram)
    register(sec2, "Ekart", "EK44551230", "LRN-1004", size=PackageSize.LARGE, condition=PackageCondition.DAMAGED,
             notes="Box corner crushed, contents rattle", arrived_at=now - timedelta(hours=5))
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
        with container.session_factory() as s:  # backdate the handover to the day after arrival
            when = now - timedelta(days=12 - i)
            s.execute(update(PickupRecord).where(PickupRecord.id == record.id).values(collected_at=when))
            s.execute(update(Package).where(Package.id == p.id).values(closed_at=when))
            s.commit()

    print("Seed complete.", DEMO_PASSWORD_NOTE)
    for inst_id, name, _, role, password in USERS:
        print(f"  {role.value:<8} {inst_id:<9} {password:<13} {name}")


if __name__ == "__main__":
    seed()
