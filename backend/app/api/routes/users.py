from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_uow, require
from app.domain.enums import Role
from app.domain.permissions import Permission
from app.infrastructure.models import User
from app.repositories.unit_of_work import UnitOfWork
from app.schemas.common import PageOut, UserBrief
from app.schemas.users import UserCreate, UserOut, UserUpdate
from app.services.users import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/learners", response_model=list[UserBrief],
            summary="Security: find a learner by institutional ID, name, email or phone")
def search_learners(q: str = Query(min_length=2, max_length=100),
                    user: User = Depends(require(Permission.LEARNER_SEARCH)),
                    uow: UnitOfWork = Depends(get_uow)) -> list[UserBrief]:
    page = UserService(uow).search(q=q, role=Role.LEARNER, active_only=True, page=1, page_size=10)
    return [UserBrief.model_validate(u) for u in page.items]


@router.get("", response_model=PageOut[UserOut])
def list_users(q: str | None = None, role: Role | None = None, page: int = Query(default=1, ge=1),
               page_size: int = Query(default=20, ge=1, le=100),
               user: User = Depends(require(Permission.USER_MANAGE)),
               uow: UnitOfWork = Depends(get_uow)) -> PageOut[UserOut]:
    result = UserService(uow).search(q=q, role=role, active_only=False, page=page, page_size=page_size)
    return PageOut(items=[UserOut.model_validate(u) for u in result.items], total=result.total,
                   page=page, page_size=page_size)


@router.post("", response_model=UserOut, status_code=201)
def create_user(body: UserCreate, user: User = Depends(require(Permission.USER_MANAGE)),
                uow: UnitOfWork = Depends(get_uow)) -> UserOut:
    return UserOut.model_validate(UserService(uow).create(actor=user, **body.model_dump()))


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: UserUpdate, user: User = Depends(require(Permission.USER_MANAGE)),
                uow: UnitOfWork = Depends(get_uow)) -> UserOut:
    return UserOut.model_validate(
        UserService(uow).update(actor=user, user_id=user_id, **body.model_dump(exclude_unset=True)))
