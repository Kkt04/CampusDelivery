from datetime import datetime, timedelta

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.time import ensure_utc, utcnow
from app.domain.enums import PackageCondition, PackageSize, PackageStatus
from app.schemas.common import ORMModel, UserBrief


class RegisterPackageRequest(BaseModel):
    courier_name: str = Field(min_length=2, max_length=80)
    tracking_id: str | None = Field(default=None, max_length=64)
    recipient_institutional_id: str | None = Field(default=None, max_length=32)
    recipient_hint: str | None = Field(default=None, max_length=200,
                                       description="Name/text on the label when the learner is unknown")
    size: PackageSize = PackageSize.SMALL
    condition: PackageCondition = PackageCondition.GOOD
    condition_notes: str | None = Field(default=None, max_length=500)
    arrived_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("tracking_id", "recipient_institutional_id", "recipient_hint", "condition_notes", "notes")
    @classmethod
    def _blank_to_none(cls, value: str | None) -> str | None:
        return value.strip() or None if isinstance(value, str) else value

    @field_validator("tracking_id")
    @classmethod
    def _tracking_format(cls, value: str | None) -> str | None:
        if value and not all(ch.isalnum() or ch in "- " for ch in value):
            raise ValueError("tracking ID may contain only letters, digits, spaces and dashes")
        if value and len("".join(value.split())) < 4:
            raise ValueError("tracking ID is too short")
        return value

    @field_validator("arrived_at")
    @classmethod
    def _not_in_future(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        value = ensure_utc(value)
        if value > utcnow() + timedelta(minutes=5):
            raise ValueError("arrival time cannot be in the future")
        return value

    @model_validator(mode="after")
    def _cross_field_rules(self) -> "RegisterPackageRequest":
        if self.condition == PackageCondition.DAMAGED and not self.condition_notes:
            raise ValueError("describe the damage in condition_notes")
        if not self.recipient_institutional_id and not self.recipient_hint:
            raise ValueError("give either the learner ID or the recipient text from the label")
        return self


class StorageAssignRequest(BaseModel):
    location_id: int | None = Field(default=None, description="Omit to auto-allocate using the configured strategy")
    mark_ready: bool = False


class IdentifyRecipientRequest(BaseModel):
    learner_institutional_id: str = Field(min_length=3, max_length=32)


class TransitionRequest(BaseModel):
    target_status: PackageStatus
    reason: str | None = Field(default=None, max_length=500)


class StorageBrief(ORMModel):
    id: int
    code: str


class ActionOut(BaseModel):
    action: str
    label: str
    target_status: PackageStatus
    dedicated: bool


class PackageOut(BaseModel):
    id: int
    internal_code: str
    courier_name: str
    tracking_id: str | None
    recipient: UserBrief | None
    recipient_hint: str | None
    size: PackageSize
    condition: PackageCondition
    condition_notes: str | None
    status: PackageStatus
    status_label: str
    storage_location: StorageBrief | None
    arrived_at: datetime
    ready_at: datetime | None
    closed_at: datetime | None
    received_by: UserBrief | None
    is_overdue: bool
    notes: str | None
    available_actions: list[ActionOut]
    updated_at: datetime


class HistoryEntryOut(BaseModel):
    from_status: PackageStatus | None
    to_status: PackageStatus
    to_label: str
    reason: str | None
    changed_by: UserBrief | None
    created_at: datetime
