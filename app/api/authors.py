from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Security
from sqlalchemy.orm import Session

from app import crud
from app.api.common.pagination import PaginatedQueryParams
from app.api.dependencies.async_db_dep import DBSessionDep
from app.api.dependencies.security import get_current_active_user_or_service_account
from app.db.session import get_session
from app.schemas.author import AuthorBrief, AuthorDetail

router = APIRouter(
    tags=["Authors"],
    dependencies=[Security(get_current_active_user_or_service_account)],
)


@router.get("/authors", response_model=List[AuthorBrief])
async def get_authors(
    session: DBSessionDep,
    query: Optional[str] = Query(None, description="Query string"),
    pagination: PaginatedQueryParams = Depends(),
):
    return await crud.author.get_all_with_optional_filters(
        session, query_string=query, skip=pagination.skip, limit=pagination.limit
    )


@router.get("/authors/{author_id}", response_model=AuthorDetail)
async def get_author_detail_by_id(
    author_id: str, session: Session = Depends(get_session)
):
    return await crud.author.aget_or_404(db=session, id=author_id)
