from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud
from app.api.common.pagination import PaginatedQueryParams
from app.db.session import get_session
from app.schemas.illustrator import IllustratorBrief

router = APIRouter(
    tags=["Authors"]
)


@router.get("/illustrators", response_model=List[IllustratorBrief])
async def get_illustrators(
        pagination: PaginatedQueryParams = Depends(),
        session: Session = Depends(get_session)
):
    return crud.illustrator.get_all(
        session,
        skip=pagination.skip,
        limit=pagination.limit)


@router.get("/illustrators/{illustrator-id}", response_model=IllustratorBrief)
async def get_illustrator_by_id(
        illustrator_id: str,
        session: Session = Depends(get_session)
):
    return crud.illustrator.get_or_404(db=session, id=illustrator_id)

