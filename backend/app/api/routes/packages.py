from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, Query, Response

from app.api.dependencies import get_current_user, get_settings_dep, get_uow, idempotency_key, require
from app.api.presenters import present_history, present_package
from app.container import container
from app.core.config import Settings
from app.core.exceptions import NotFoundError
from app.core.time import utcnow
from app.domain.enums import PackageCondition, PackageStatus, Role
from app.domain.permissions import Permission, can_view_package
from app.infrastructure.models import User
from app.repositories.filters import PackageFilters
from app.repositories.unit_of_work import UnitOfWork
from app.schemas.common import PageOut
from app.schemas.packages import (
    HistoryEntryOut,
    IdentifyRecipientRequest,
    InitiateReturnRequest,
    PackageOut,
    RegisterPackageRequest,
    ReturnRequest,
    StorageAssignRequest,
    TransitionRequest,
)
from app.services.lifecycle import PackageLifecycleService
from app.services.package_intake import PackageIntakeService
from app.services.storage_allocation import StorageAllocationService

router = APIRouter(prefix="/packages", tags=["Packages"])


def _day_start(d: date) -> datetime:
    return datetime.combine(d, time.min, tzinfo=timezone.utc)


@router.post("", response_model=PackageOut, status_code=201, summary="Register an incoming package")
def register_package(body: RegisterPackageRequest, response: Response,
                     key: str | None = Depends(idempotency_key),
                     user: User = Depends(require(Permission.PACKAGE_REGISTER)),
                     uow: UnitOfWork = Depends(get_uow),
                     settings: Settings = Depends(get_settings_dep)) -> PackageOut:
    package, replayed = PackageIntakeService(uow).register(actor=user, idempotency_key=key, **body.model_dump())
    if replayed:
        response.status_code = 200
        response.headers["Idempotent-Replayed"] = "true"
    return present_package(package, user, utcnow(), settings)


@router.get("", response_model=PageOut[PackageOut], summary="Search packages (learners: own packages only)")
def list_packages(
    q: str | None = Query(default=None, max_length=100),
    status: list[PackageStatus] = Query(default=[]),
    condition: PackageCondition | None = None,
    overdue: bool = False,
    arrived_from: date | None = None,
    arrived_to: date | None = None,
    storage_location_id: int | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
    settings: Settings = Depends(get_settings_dep),
) -> PageOut[PackageOut]:
    filters = PackageFilters(
        q=q, statuses=status, condition=condition, overdue_only=overdue,
        overdue_deadline_days=settings.collection_deadline_days,
        arrived_from=_day_start(arrived_from) if arrived_from else None,
        arrived_to=_day_start(arrived_to) + timedelta(days=1) if arrived_to else None,
        storage_location_id=storage_location_id,
    )
    if user.role == Role.LEARNER:
        PackageIntakeService(uow).claim_packages_for_learner(user)
        filters.recipient_id = user.id  # server-side scoping; cannot be overridden by the client
        filters.storage_location_id = None
    now = utcnow()
    result = uow.packages.search(filters, page, page_size, now)
    return PageOut(items=[present_package(p, user, now, settings) for p in result.items],
                   total=result.total, page=page, page_size=page_size)


def _visible_package(uow: UnitOfWork, package_id: int, user: User):  # noqa: ANN202
    package = uow.packages.get(package_id)
    # 404 (not 403) for other learners' packages: do not reveal that the ID exists.
    if package is None or not can_view_package(user.role, user.id, package.recipient_id):
        raise NotFoundError("Package not found")
    return package


@router.get("/{package_id}", response_model=PackageOut)
def get_package(package_id: int, user: User = Depends(get_current_user), uow: UnitOfWork = Depends(get_uow),
                settings: Settings = Depends(get_settings_dep)) -> PackageOut:
    return present_package(_visible_package(uow, package_id, user), user, utcnow(), settings)


@router.get("/{package_id}/history", response_model=list[HistoryEntryOut])
def package_history(package_id: int, user: User = Depends(get_current_user),
                    uow: UnitOfWork = Depends(get_uow)) -> list[HistoryEntryOut]:
    _visible_package(uow, package_id, user)
    return [present_history(h, user) for h in uow.packages.history(package_id)]


@router.post("/{package_id}/storage", response_model=PackageOut, summary="Assign or move storage")
def assign_storage(package_id: int, body: StorageAssignRequest,
                   user: User = Depends(require(Permission.PACKAGE_MANAGE)),
                   uow: UnitOfWork = Depends(get_uow), settings: Settings = Depends(get_settings_dep)) -> PackageOut:
    package = StorageAllocationService(uow, container.allocation_strategy).assign(
        package_id=package_id, actor=user, location_id=body.location_id, mark_ready=body.mark_ready)
    return present_package(package, user, utcnow(), settings)


@router.post("/{package_id}/recipient", response_model=PackageOut, summary="Identify an unknown recipient")
def identify_recipient(package_id: int, body: IdentifyRecipientRequest,
                       user: User = Depends(require(Permission.PACKAGE_MANAGE)),
                       uow: UnitOfWork = Depends(get_uow),
                       settings: Settings = Depends(get_settings_dep)) -> PackageOut:
    package = PackageIntakeService(uow).identify_recipient(
        package_id=package_id, learner_institutional_id=body.learner_institutional_id, actor=user)
    return present_package(package, user, utcnow(), settings)


@router.post("/{package_id}/return-request", response_model=PackageOut, status_code=201,
             summary="Ask for a package to be sent back to the courier")
def request_return(package_id: int, body: ReturnRequest,
                   user: User = Depends(require(Permission.PACKAGE_REQUEST_RETURN)),
                   uow: UnitOfWork = Depends(get_uow),
                   settings: Settings = Depends(get_settings_dep)) -> PackageOut:
    package = PackageLifecycleService(uow).request_return(
        package_id=package_id, actor=user, reason=body.reason)
    return present_package(package, user, utcnow(), settings)


@router.post("/return-initiate", response_model=PackageOut, status_code=201,
             summary="Learner: initiate a parcel return request")
def initiate_return(body: InitiateReturnRequest,
                    user: User = Depends(require(Permission.PACKAGE_REQUEST_RETURN)),
                    uow: UnitOfWork = Depends(get_uow),
                    settings: Settings = Depends(get_settings_dep)) -> PackageOut:
    package = PackageLifecycleService(uow).initiate_learner_return(
        actor=user, package_id=body.package_id, courier_name=body.courier_name,
        tracking_id=body.tracking_id, reason=body.reason, size=body.size, notes=body.notes)
    return present_package(package, user, utcnow(), settings)


@router.post("/{package_id}/transitions", response_model=PackageOut, summary="Apply a lifecycle transition")
def transition(package_id: int, body: TransitionRequest,
               user: User = Depends(require(Permission.PACKAGE_MANAGE)),
               uow: UnitOfWork = Depends(get_uow), settings: Settings = Depends(get_settings_dep)) -> PackageOut:
    package = PackageLifecycleService(uow).transition(
        package_id=package_id, target=body.target_status, actor=user, reason=body.reason)
    return present_package(package, user, utcnow(), settings)
