from typing import Any

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_current_user, get_uow
from app.container import container
from app.core.rate_limit import resolve_client_ip
from app.infrastructure.models import User
from app.repositories.unit_of_work import UnitOfWork
from app.schemas.users import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    ResetPasswordWithTokenRequest,
    SignupRequest,
    TokenOut,
    UserOut,
)
from app.services.users import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenOut, summary="Sign in with institutional ID or email")
def login(body: LoginRequest, request: Request, uow: UnitOfWork = Depends(get_uow)) -> TokenOut:
    client_ip = resolve_client_ip(request, container.settings.trusted_proxy_list)
    token, expires_in, refresh_token, user = AuthService(uow, container.login_limiter).login(
        body.identifier, body.password, client_ip
    )
    return TokenOut(
        access_token=token,
        expires_in=expires_in,
        refresh_token=refresh_token,
        user=UserOut.model_validate(user),
    )


@router.post("/signup", response_model=TokenOut, status_code=201, summary="Create a learner account and sign in")
def signup(body: SignupRequest, uow: UnitOfWork = Depends(get_uow)) -> TokenOut:
    token, expires_in, refresh_token, user = AuthService(uow, container.login_limiter).signup(
        institutional_id=body.institutional_id,
        full_name=body.full_name,
        email=body.email,
        phone=body.phone,
        password=body.password,
    )
    return TokenOut(
        access_token=token,
        expires_in=expires_in,
        refresh_token=refresh_token,
        user=UserOut.model_validate(user),
    )


@router.post("/refresh", response_model=TokenOut, summary="Refresh access token using refresh token")
def refresh(body: RefreshTokenRequest, uow: UnitOfWork = Depends(get_uow)) -> TokenOut:
    token, expires_in, refresh_token, user = AuthService(uow, container.login_limiter).refresh_session(
        body.refresh_token
    )
    return TokenOut(
        access_token=token,
        expires_in=expires_in,
        refresh_token=refresh_token,
        user=UserOut.model_validate(user),
    )


@router.post("/forgot-password", summary="Request single-use 15-minute password reset token")
def forgot_password(body: ForgotPasswordRequest, request: Request, uow: UnitOfWork = Depends(get_uow)) -> dict[str, Any]:
    client_ip = resolve_client_ip(request, container.settings.trusted_proxy_list)
    return AuthService(uow, container.login_limiter).request_password_reset(body.identifier, client_ip)


@router.post("/reset-password", response_model=TokenOut, summary="Submit reset token and new password")
def reset_password(body: ResetPasswordWithTokenRequest, uow: UnitOfWork = Depends(get_uow)) -> TokenOut:
    token, expires_in, refresh_token, user = AuthService(uow, container.login_limiter).reset_password_with_token(
        token=body.token, new_password=body.new_password
    )
    return TokenOut(
        access_token=token,
        expires_in=expires_in,
        refresh_token=refresh_token,
        user=UserOut.model_validate(user),
    )


@router.post("/change-password", summary="Change password for authenticated user")
def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
) -> dict[str, str]:
    AuthService(uow, container.login_limiter).change_password(
        user=user, current_password=body.current_password, new_password=body.new_password
    )
    return {"message": "Password updated successfully."}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(user)
