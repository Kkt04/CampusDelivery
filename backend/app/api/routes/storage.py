from fastapi import APIRouter, Depends

from app.api.dependencies import get_uow, require
from app.domain.permissions import Permission
from app.infrastructure.models import User
from app.repositories.unit_of_work import UnitOfWork
from app.schemas.misc import StorageLocationCreate, StorageLocationOut, StorageLocationUpdate
from app.services.storage_locations import StorageLocationService

router = APIRouter(prefix="/storage-locations", tags=["Storage"])


@router.get("", response_model=list[StorageLocationOut])
def list_locations(active_only: bool = False, user: User = Depends(require(Permission.STORAGE_VIEW)),
                   uow: UnitOfWork = Depends(get_uow)) -> list[StorageLocationOut]:
    return [StorageLocationOut.model_validate(loc) for loc in StorageLocationService(uow).list_locations(active_only)]


@router.post("", response_model=StorageLocationOut, status_code=201)
def create_location(body: StorageLocationCreate, user: User = Depends(require(Permission.STORAGE_MANAGE)),
                    uow: UnitOfWork = Depends(get_uow)) -> StorageLocationOut:
    return StorageLocationOut.model_validate(StorageLocationService(uow).create(actor=user, **body.model_dump()))


@router.patch("/{location_id}", response_model=StorageLocationOut)
def update_location(location_id: int, body: StorageLocationUpdate,
                    user: User = Depends(require(Permission.STORAGE_MANAGE)),
                    uow: UnitOfWork = Depends(get_uow)) -> StorageLocationOut:
    location = StorageLocationService(uow).update(actor=user, location_id=location_id,
                                                  **body.model_dump(exclude_unset=True))
    return StorageLocationOut.model_validate(location)
