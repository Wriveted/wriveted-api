from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud
from app.api.common.pagination import PaginatedQueryParams
from app.db.session import get_session
from app.schemas.author import AuthorBrief, AuthorDetail

router = APIRouter(
    tags=["Authors"]
)


@router.get("/authors", response_model=List[AuthorBrief])
async def get_authors(
        pagination: PaginatedQueryParams = Depends(),
        session: Session = Depends(get_session)
):
    return crud.author.get_all(
        session,
        skip=pagination.skip,
        limit=pagination.limit)


@router.get("/authors/{author-id}", response_model=AuthorDetail)
async def get_author_detail_by_id(
        work_id: str,
        session: Session = Depends(get_session)
):
    return crud.author.get_or_404(db=session, id=work_id)

