from fastapi import APIRouter, Depends, HTTPException, Path, Query, Security
from starlette import status
from structlog import get_logger

from app import crud
from app.api.common.pagination import PaginatedQueryParams
from app.api.dependencies.async_db_dep import DBSessionDep
from app.api.dependencies.security import (
    get_current_active_superuser_or_backend_service_account,
)
from app.models import ContentType
from app.schemas.cms_content import CMSContentResponse
from app.schemas.pagination import Pagination

logger = get_logger()

router = APIRouter(
    tags=["Digital Content Management System"],
    dependencies=[Security(get_current_active_superuser_or_backend_service_account)],
)


@router.get("/content/{content_type}", response_model=CMSContentResponse)
async def get_cms_content(
    session: DBSessionDep,
    content_type: ContentType = Path(
        description="What type of content to return",
    ),
    query: str | None = Query(
        None,
        description="A query string to match against content",
    ),
    # user_id: UUID = Query(
    #     None, description="Filter content that are associated with or created by a user"
    # ),
    jsonpath_match: str = Query(
        None,
        description="Filter using a JSONPath over the content. The resulting value must be a boolean expression.",
    ),
    pagination: PaginatedQueryParams = Depends(),
):
    """
    Get a filtered and paginated list of content by content type.
    """
    try:
        data = await crud.content.aget_all_with_optional_filters(
            session,
            content_type=content_type,
            query_string=query,
            # user=user,
            jsonpath_match=jsonpath_match,
            skip=pagination.skip,
            limit=pagination.limit,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e

    return CMSContentResponse(
        pagination=Pagination(**pagination.to_dict(), total=None), data=data
    )
