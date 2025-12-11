from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Security
from sqlalchemy.orm import Session

from app.api.common.pagination import PaginatedQueryParams
from app.api.dependencies.security import get_current_active_user_or_service_account
from app.db.session import get_session
from app.repositories.author_repository import author_repository
from app.schemas.author import AuthorBrief, AuthorDetail

router = APIRouter(
    tags=["Authors"],
    dependencies=[Security(get_current_active_user_or_service_account)],
)


@router.get("/authors", response_model=List[AuthorBrief])
def get_authors(
    session: Session = Depends(get_session),
    query: Optional[str] = Query(None, description="Query string"),
    pagination: PaginatedQueryParams = Depends(),
):
    return author_repository.search(
        session, query_string=query, skip=pagination.skip, limit=pagination.limit
    )


@router.get("/authors/{author_id}", response_model=AuthorDetail)
def get_author_detail_by_id(author_id: str, session: Session = Depends(get_session)):
    return author_repository.get_or_404(db=session, id=int(author_id))
