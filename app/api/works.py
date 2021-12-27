from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud
from app.api.common.pagination import PaginatedQueryParams
from app.db.session import get_session
from app.schemas.work import WorkBrief, WorkDetail

router = APIRouter(
    tags=["Books"]
)


@router.get("/works", response_model=List[WorkBrief])
async def get_works(
        pagination: PaginatedQueryParams = Depends(),
        session: Session = Depends(get_session)
):
    return crud.work.get_all(session, skip=pagination.skip, limit=pagination.limit)


@router.get("/works/{work_id}", response_model=WorkDetail)
async def get_work_by_id(
        work_id: str,
        session: Session = Depends(get_session)
):
    return crud.work.get_or_404(db=session, id=work_id)

