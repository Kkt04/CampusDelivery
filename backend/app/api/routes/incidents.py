from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_current_user, get_uow, require
from app.api.presenters import present_incident
from app.domain.enums import IncidentStatus, IncidentType
from app.domain.permissions import Permission, has_permission
from app.core.exceptions import PermissionDeniedError
from app.infrastructure.models import User
from app.repositories.filters import IncidentFilters
from app.repositories.unit_of_work import UnitOfWork
from app.schemas.common import PageOut
from app.schemas.misc import IncidentCommentCreate, IncidentCreate, IncidentOut, IncidentResolve
from app.services.incidents import IncidentService

router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.post("", response_model=IncidentOut, status_code=201,
             summary="Report an incident (learners: issue about their own package)")
def report_incident(body: IncidentCreate, user: User = Depends(require(Permission.INCIDENT_REPORT)),
                    uow: UnitOfWork = Depends(get_uow)) -> IncidentOut:
    incident = IncidentService(uow).report(actor=user, package_id=body.package_id, kind=body.type,
                                           description=body.description, escalate=body.escalate)
    return present_incident(incident)


@router.get("", response_model=PageOut[IncidentOut])
def list_incidents(status: IncidentStatus | None = None, type: IncidentType | None = None,
                   package_id: int | None = None, page: int = Query(default=1, ge=1),
                   page_size: int = Query(default=20, ge=1, le=100),
                   user: User = Depends(get_current_user), uow: UnitOfWork = Depends(get_uow)) -> PageOut[IncidentOut]:
    if not (has_permission(user.role, Permission.INCIDENT_VIEW_ALL)
            or has_permission(user.role, Permission.INCIDENT_REPORT)):
        raise PermissionDeniedError("You do not have permission to do this.")
    result = IncidentService(uow).search(actor=user, filters=IncidentFilters(status=status, type=type,
                                       package_id=package_id), page=page, page_size=page_size)
    return PageOut(items=[present_incident(i) for i in result.items], total=result.total,
                   page=page, page_size=page_size)


@router.get("/{incident_id}", response_model=IncidentOut)
def get_incident(incident_id: int, user: User = Depends(get_current_user),
                 uow: UnitOfWork = Depends(get_uow)) -> IncidentOut:
    return present_incident(IncidentService(uow).get(actor=user, incident_id=incident_id))


@router.post("/{incident_id}/comments", response_model=IncidentOut)
def add_incident_comment(incident_id: int, body: IncidentCommentCreate,
                         user: User = Depends(get_current_user),
                         uow: UnitOfWork = Depends(get_uow)) -> IncidentOut:
    return present_incident(IncidentService(uow).add_comment(
        actor=user, incident_id=incident_id, message=body.message))


@router.post("/{incident_id}/resolve", response_model=IncidentOut)
def resolve_incident(incident_id: int, body: IncidentResolve,
                     user: User = Depends(require(Permission.INCIDENT_RESOLVE)),
                     uow: UnitOfWork = Depends(get_uow)) -> IncidentOut:
    return present_incident(IncidentService(uow).resolve(actor=user, incident_id=incident_id,
                                                         resolution_note=body.resolution_note))
