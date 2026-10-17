from fastapi import APIRouter, Depends, Query, Response

from app.api.dependencies import get_current_user, get_settings_dep, get_uow, idempotency_key, require
from app.core.exceptions import PermissionDeniedError
from app.api.presenters import present_package, present_pickup
from app.core.config import Settings
from app.core.time import utcnow
from app.domain.permissions import Permission, has_permission
from app.infrastructure.models import User
from app.repositories.unit_of_work import UnitOfWork
from app.schemas.common import PageOut
from app.schemas.pickups import PickupCodeOut, PickupRecordOut, PickupVerificationOut, PickupVerifyRequest
from app.services.pickup import PickupService

router = APIRouter(tags=["Pickup"])


@router.post("/packages/{package_id}/pickup-request", response_model=PickupCodeOut, status_code=201,
             summary="Learner: request pickup and receive a one-time code")
def request_pickup(package_id: int, user: User = Depends(require(Permission.PICKUP_REQUEST)),
                   uow: UnitOfWork = Depends(get_uow), settings: Settings = Depends(get_settings_dep)) -> PickupCodeOut:
    issued = PickupService(uow, settings).request_pickup(package_id=package_id, learner=user)
    return PickupCodeOut(package_id=issued.package.id, internal_code=issued.package.internal_code,
                         code=issued.code, expires_at=issued.expires_at)


@router.post("/pickups/verify", response_model=PickupVerificationOut,
             summary="Security: check a learner's code without handing over")
def verify_pickup(body: PickupVerifyRequest, user: User = Depends(require(Permission.PICKUP_HANDOVER)),
                  uow: UnitOfWork = Depends(get_uow),
                  settings: Settings = Depends(get_settings_dep)) -> PickupVerificationOut:
    package = PickupService(uow, settings).verify(
        package_code=body.package_code, learner_institutional_id=body.learner_institutional_id,
        code=body.code, actor=user)
    return PickupVerificationOut(verified=True, package=present_package(package, user, utcnow(), settings))


@router.post("/pickups/complete", response_model=PickupRecordOut, status_code=201,
             summary="Security: verify the code and hand the package over (idempotent with Idempotency-Key)")
def complete_pickup(body: PickupVerifyRequest, response: Response, key: str | None = Depends(idempotency_key),
                    user: User = Depends(require(Permission.PICKUP_HANDOVER)),
                    uow: UnitOfWork = Depends(get_uow),
                    settings: Settings = Depends(get_settings_dep)) -> PickupRecordOut:
    record, replayed = PickupService(uow, settings).complete(
        package_code=body.package_code, learner_institutional_id=body.learner_institutional_id,
        code=body.code, actor=user, idempotency_key=key)
    if replayed:
        response.status_code = 200
        response.headers["Idempotent-Replayed"] = "true"
    return present_pickup(record, user)


@router.get("/pickups", response_model=PageOut[PickupRecordOut],
            summary="Collection history (learners: own; staff: all)")
def pickup_history(page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100),
                   user: User = Depends(get_current_user), uow: UnitOfWork = Depends(get_uow),
                   settings: Settings = Depends(get_settings_dep)) -> PageOut[PickupRecordOut]:
    if has_permission(user.role, Permission.PICKUP_HISTORY_ALL):
        learner_id = None
    elif has_permission(user.role, Permission.PACKAGE_VIEW_OWN):
        learner_id = user.id
    else:
        raise PermissionDeniedError("You do not have permission to do this.")
    result = PickupService(uow, settings).history(learner_id=learner_id, page=page, page_size=page_size)
    return PageOut(items=[present_pickup(r, user) for r in result.items], total=result.total,
                   page=page, page_size=page_size)
