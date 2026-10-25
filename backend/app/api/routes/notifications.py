from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_current_user, get_uow, require
from app.container import container
from app.domain.permissions import Permission
from app.infrastructure.models import User
from app.repositories.unit_of_work import UnitOfWork
from app.schemas.common import PageOut
from app.schemas.misc import NotificationOut
from app.services.notifications import NotificationService
from app.services.audit import AuditService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=PageOut[NotificationOut], summary="My in-app notifications")
def my_notifications(page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100),
                     user: User = Depends(get_current_user),
                     uow: UnitOfWork = Depends(get_uow)) -> PageOut[NotificationOut]:
    result = NotificationService(uow).list_for(user, page, page_size)
    return PageOut(items=[NotificationOut.model_validate(n) for n in result.items], total=result.total,
                   page=page, page_size=page_size)


@router.get("/unread-count")
def unread_count(user: User = Depends(get_current_user), uow: UnitOfWork = Depends(get_uow)) -> dict[str, int]:
    return {"unread": NotificationService(uow).unread_count(user)}


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: int, user: User = Depends(get_current_user),
              uow: UnitOfWork = Depends(get_uow)) -> NotificationOut:
    return NotificationOut.model_validate(NotificationService(uow).mark_read(user, notification_id))


@router.post("/read-all")
def mark_all_read(user: User = Depends(get_current_user), uow: UnitOfWork = Depends(get_uow)) -> dict[str, int]:
    return {"updated": NotificationService(uow).mark_all_read(user)}


@router.post("/retry-failed", summary="Admin: retry FAILED or stuck PENDING notifications")
def retry_failed(user: User = Depends(require(Permission.NOTIFICATION_ADMIN)),
                 uow: UnitOfWork = Depends(get_uow)) -> dict[str, int]:
    result = container.dispatcher.retry(container.settings.notification_max_attempts)
    AuditService(uow.audit).record(user, "notification.retry", "notification", None, result)
    uow.commit()
    return result


@router.post("/sweep-overdue", summary="Trigger automated overdue daily notification sweep")
def sweep_overdue(user: User = Depends(get_current_user),
                  uow: UnitOfWork = Depends(get_uow)) -> dict[str, int]:
    result = NotificationService(uow, channels=container.dispatcher.channels).sweep_overdue()
    AuditService(uow.audit).record(user, "notification.sweep_overdue", "package", None, result)
    uow.commit()
    return result
