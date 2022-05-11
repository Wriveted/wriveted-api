from typing import List, Optional, Union
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Security
from sqlalchemy.orm import Session

from app import crud
from app.api.common.pagination import PaginatedQueryParams
from app.api.dependencies.school import get_school_from_raw_id, get_school_from_wriveted_id
from app.api.dependencies.security import get_current_active_user_or_service_account
from app.db.session import get_session
from app.models.event import EventLevel
from app.models.school import School
from app.models.service_account import ServiceAccount
from app.models.user import User
from app.schemas.event import EventBrief, EventCreateIn, EventDetail

from starlette import status

router = APIRouter(
    tags=["Events"],
    dependencies=[Security(get_current_active_user_or_service_account)],
)


@router.post("/events", response_model=EventDetail)
async def create(
    data: EventCreateIn,
    account: Union[ServiceAccount, User] = Depends(get_current_active_user_or_service_account),
    session: Session = Depends(get_session),
):
    school = crud.school.get_by_wriveted_id_or_404(
        db=session, wriveted_id=data.school_id
    ) if data.school_id else None

    return crud.event.create(
        session=session,
        title=data.title,
        description=data.description,
        info=data.info,
        level=data.level,
        school=school,
        account=account
    )


@router.get("/events", response_model=List[EventDetail])
async def get_events(
    query: str = None,
    level: EventLevel = None,
    school_id: UUID = None,
    user_id: UUID = None,
    service_account_id: UUID = None,
    pagination: PaginatedQueryParams = Depends(),
    session: Session = Depends(get_session),
):
    if(user_id and service_account_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Must only provide one of user_id or service_account_id"
        )
        
    account = crud.user.get_or_404(
        db=session, id=user_id
    ) if user_id else (
        crud.service_account.get_or_404(
            db=session, id=service_account_id
        ) if service_account_id else None
    )

    school = crud.school.get_by_wriveted_id_or_404(
        db=session, wriveted_id=school_id
    ) if school_id else None

    return crud.event.get_all_with_optional_filters(
        session, 
        query_string=query,
        level=level,
        school=school,
        account=account,
        skip=pagination.skip, 
        limit=pagination.limit
    )