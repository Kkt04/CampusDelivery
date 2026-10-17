from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.domain.enums import Role
from app.schemas.common import ORMModel


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=254, description="Institutional ID or email")
    password: str = Field(min_length=1, max_length=128)


class SignupRequest(BaseModel):
    institutional_id: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9-]+$")
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=20, pattern=r"^\+?[0-9 -]{7,20}$")
    password: str = Field(min_length=8, max_length=128)


class UserOut(ORMModel):
    id: int
    institutional_id: str
    full_name: str
    email: str
    phone: str | None
    role: Role
    is_active: bool
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class UserCreate(BaseModel):
    institutional_id: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9-]+$")
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=20, pattern=r"^\+?[0-9 -]{7,20}$")
    role: Role
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=20)
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
