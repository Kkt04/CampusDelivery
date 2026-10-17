from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_settings_dep, get_uow, require
from app.api.presenters import present_audit
from app.core.config import Settings
from app.core.time import utcnow
from app.domain.permissions import Permission
from app.infrastructure.models import User
from app.repositories.filters import AuditFilters
from app.repositories.unit_of_work import UnitOfWork
from app.schemas.common import PageOut
from app.schemas.misc import AuditLogOut, DailyReportRow, DashboardOut
from app.services.reports import ReportService

router = APIRouter(tags=["Reports & audit"])


@router.get("/reports/dashboard", response_model=DashboardOut)
def dashboard(user: User = Depends(require(Permission.PACKAGE_VIEW_ALL)), uow: UnitOfWork = Depends(get_uow),
              settings: Settings = Depends(get_settings_dep)) -> DashboardOut:
    return DashboardOut(**ReportService(uow, settings).dashboard(utcnow()))


@router.get("/reports/daily", response_model=list[DailyReportRow], summary="Received vs collected per day")
def daily_report(date_from: date | None = None, date_to: date | None = None,
                 user: User = Depends(require(Permission.REPORT_VIEW)), uow: UnitOfWork = Depends(get_uow),
                 settings: Settings = Depends(get_settings_dep)) -> list[DailyReportRow]:
    today = utcnow().date()
    date_to = date_to or today
    date_from = date_from or date_to - timedelta(days=13)
    return [DailyReportRow(**row) for row in ReportService(uow, settings).daily(date_from, date_to)]


@router.get("/audit-logs", response_model=PageOut[AuditLogOut])
def audit_logs(action: str | None = Query(default=None, max_length=64), entity_type: str | None = None,
               entity_id: str | None = None, actor_id: int | None = None,
               date_from: date | None = None, date_to: date | None = None,
               page: int = Query(default=1, ge=1), page_size: int = Query(default=50, ge=1, le=200),
               user: User = Depends(require(Permission.AUDIT_VIEW)),
               uow: UnitOfWork = Depends(get_uow)) -> PageOut[AuditLogOut]:
    def _start(d: date) -> datetime:
        return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)

    filters = AuditFilters(action=action, entity_type=entity_type, entity_id=entity_id, actor_id=actor_id,
                           date_from=_start(date_from) if date_from else None,
                           date_to=_start(date_to) + timedelta(days=1) if date_to else None)
    result = uow.audit.search(filters, page, page_size)
    return PageOut(items=[present_audit(a) for a in result.items], total=result.total, page=page,
                   page_size=page_size)
