from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_current_user, get_uow
from app.container import container
from app.infrastructure.models import User
from app.repositories.unit_of_work import UnitOfWork
from app.schemas.users import LoginRequest, TokenOut, UserOut
from app.services.users import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenOut, summary="Sign in with institutional ID or email")
def login(body: LoginRequest, request: Request, uow: UnitOfWork = Depends(get_uow)) -> TokenOut:
    client_ip = request.client.host if request.client else "unknown"
    token, expires_in, user = AuthService(uow, container.login_limiter).login(body.identifier, body.password, client_ip)
    return TokenOut(access_token=token, expires_in=expires_in, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(user)
