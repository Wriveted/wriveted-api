from typing import List

from fastapi import Depends, APIRouter
from sqlalchemy.orm import Session
from structlog import get_logger

from app import crud
from app.api.common.pagination import PaginatedQueryParams
from app.api.dependencies.security import get_current_active_superuser_or_backend_service_account
from app.db.session import get_session
from app.schemas.user import UserBrief, UserDetail

logger = get_logger()

router = APIRouter(
    tags=["Security"],
    dependencies=[
        Depends(get_current_active_superuser_or_backend_service_account)
    ]
)


@router.get("/users", response_model=List[UserBrief])
async def get_users(
        pagination: PaginatedQueryParams = Depends(),
        session: Session = Depends(get_session)
):
    """
    List all users
    """
    logger.info("Listing users")
    return crud.user.get_all(db=session, skip=pagination.skip, limit=pagination.limit)


@router.get("/user/{uuid}", response_model=UserDetail)
async def get_user(
        uuid: str,
        session: Session = Depends(get_session)
):
    logger.info("Retrieving details on one user")
    return crud.user.get(db=session, id=uuid)
