"""Use cases: manage storage locations (operations admin)."""
from app.core.exceptions import ConflictError, NotFoundError, ValidationFailedError
from app.domain.enums import PackageSize
from app.infrastructure.models import StorageLocation, User
from app.repositories.unit_of_work import UnitOfWork
from app.services.audit import AuditService


class StorageLocationService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow
        self._audit = AuditService(uow.audit)

    def list_locations(self, active_only: bool = False) -> list[StorageLocation]:
        return self._uow.storage.list_locations(active_only)

    def create(self, *, actor: User, code: str, description: str | None, capacity: int,
               max_package_size: PackageSize) -> StorageLocation:
        code = code.strip().upper()
        if self._uow.storage.get_by_code(code):
            raise ConflictError(f"Storage location {code} already exists.", code="STORAGE_CODE_EXISTS")
        location = self._uow.storage.add(StorageLocation(
            code=code, description=description, capacity=capacity,
            max_package_size=max_package_size, occupied_count=0, is_active=True))
        self._audit.record(actor, "storage.created", "storage_location", location.id,
                           {"code": code, "capacity": capacity})
        self._uow.commit()
        return location

    def update(self, *, actor: User, location_id: int, description: str | None = None,
               capacity: int | None = None, max_package_size: PackageSize | None = None,
               is_active: bool | None = None) -> StorageLocation:
        location = self._uow.storage.get(location_id)
        if location is None:
            raise NotFoundError("Storage location not found")
        self._uow.session.refresh(location)  # read the latest occupied_count
        changes: dict[str, object] = {}
        if capacity is not None and capacity != location.capacity:
            if capacity < location.occupied_count:
                raise ValidationFailedError(
                    f"{location.code} holds {location.occupied_count} packages; capacity cannot go below that.",
                    code="CAPACITY_BELOW_OCCUPANCY")
            changes["capacity"] = (location.capacity, capacity)
            location.capacity = capacity
        if max_package_size is not None and max_package_size != location.max_package_size:
            changes["max_package_size"] = (location.max_package_size.value, max_package_size.value)
            location.max_package_size = max_package_size
        if description is not None and description != location.description:
            changes["description"] = (location.description, description)
            location.description = description
        if is_active is not None and is_active != location.is_active:
            # Deactivating keeps current packages in place but blocks new allocations.
            changes["is_active"] = (location.is_active, is_active)
            location.is_active = is_active
        if changes:
            self._audit.record(actor, "storage.updated", "storage_location", location.id,
                               {k: {"old": o, "new": n} for k, (o, n) in changes.items()})
        self._uow.commit()
        return location
