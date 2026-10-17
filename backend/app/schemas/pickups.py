from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import UserBrief
from app.schemas.packages import PackageOut


class PickupCodeOut(BaseModel):
    package_id: int
    internal_code: str
    code: str = Field(description="Shown once. Only a hash is stored on the server.")
    expires_at: datetime


class PickupVerifyRequest(BaseModel):
    package_code: str = Field(min_length=6, max_length=24)
    learner_institutional_id: str = Field(min_length=3, max_length=32)
    code: str = Field(pattern=r"^\d{6}$")


class PickupVerificationOut(BaseModel):
    verified: bool
    package: PackageOut


class PickupRecordOut(BaseModel):
    id: int
    package_id: int
    internal_code: str
    courier_name: str
    learner_id: int
    handed_over_by: UserBrief | None
    storage_location_code: str | None
    collected_at: datetime
