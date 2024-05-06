from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.params import Query
from structlog import get_logger

from app.api.common.pagination import PaginatedQueryParams
from app.api.dependencies.async_db_dep import DBSessionDep
from app.api.dependencies.security import get_current_active_user_or_service_account
from app.schemas.search_results import SearchQueryInput, SearchResults
from app.services.search import book_search

router = APIRouter(
    tags=["Books"], dependencies=[Depends(get_current_active_user_or_service_account)]
)

logger = get_logger()


@router.get(
    "/search",
    response_model=SearchResults,
)
async def get_book_search(
    session: DBSessionDep,
    query: Optional[str] = Query(None, description="Query string"),
    # author_id: Optional[int] = Query(None, description="Author's Wriveted Id"),
    # type: Optional[WorkType] = Query(WorkType.BOOK),
    pagination: PaginatedQueryParams = Depends(),
):
    logger.info("Searching for books", query=query)
    results = await book_search(session, query, pagination)
    logger.info("Search results", results=results)
    return SearchResults(
        event_id="",
        input=SearchQueryInput(query=query),
        books=results,
    )
