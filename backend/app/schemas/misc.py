from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.domain.enums import (
    IncidentStatus,
    IncidentType,
    NotificationChannelType,
    NotificationStatus,
    PackageSize,
)
from app.schemas.common import ORMModel, UserBrief


class StorageLocationOut(ORMModel):
    id: int
    code: str
    description: str | None
    capacity: int
    occupied_count: int
    max_package_size: PackageSize
    is_active: bool


class StorageLocationCreate(BaseModel):
    code: str = Field(min_length=2, max_length=20, pattern=r"^[A-Za-z0-9-]+$")
    description: str | None = Field(default=None, max_length=200)
    capacity: int = Field(gt=0, le=500)
    max_package_size: PackageSize = PackageSize.MEDIUM


class StorageLocationUpdate(BaseModel):
    description: str | None = Field(default=None, max_length=200)
    capacity: int | None = Field(default=None, gt=0, le=500)
    max_package_size: PackageSize | None = None
    is_active: bool | None = None


class NotificationOut(ORMModel):
    id: int
    package_id: int | None
    channel: NotificationChannelType
    title: str
    message: str
    delivery_status: NotificationStatus
    created_at: datetime
    read_at: datetime | None


class IncidentCreate(BaseModel):
    package_id: int | None = None
    type: IncidentType = IncidentType.OPERATIONAL
    description: str = Field(min_length=5, max_length=2000)
    escalate: bool = Field(default=False, description="Also move the package to UNDER_INVESTIGATION")


class IncidentResolve(BaseModel):
    resolution_note: str = Field(min_length=3, max_length=2000)


class IncidentCommentOut(BaseModel):
    id: str
    author_id: int
    author_name: str
    author_role: str
    message: str
    created_at: str


class IncidentCommentCreate(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class IncidentOut(BaseModel):
    id: int
    package_id: int | None
    package_code: str | None
    type: IncidentType
    status: IncidentStatus
    description: str
    reported_by: UserBrief
    resolved_by: UserBrief | None
    resolution_note: str | None
    comments: list[IncidentCommentOut] = Field(default_factory=list)
    created_at: datetime
    resolved_at: datetime | None


class AuditLogOut(BaseModel):
    id: int
    actor: UserBrief | None
    action: str
    entity_type: str
    entity_id: str | None
    details: dict[str, Any] | None
    created_at: datetime


class DashboardOut(BaseModel):
    by_status: dict[str, int]
    received: int
    in_custody: int
    overdue: int
    damaged_condition: int
    received_today: int
    collected_today: int
    open_incidents: int
    failed_notifications: int
    storage_capacity: int
    storage_occupied: int
    collection_deadline_days: int


class DailyReportRow(BaseModel):
    date: str
    received: int
    collected: int
