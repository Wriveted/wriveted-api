from typing import List

from fastapi import APIRouter, Depends, Security
from sqlalchemy import delete, func, update, select
from sqlalchemy.orm import Session
from structlog import get_logger

from app.api.common.pagination import PaginatedQueryParams
from app.api.dependencies.school import get_school_from_wriveted_id
from app.api.dependencies.security import get_current_active_user_or_service_account
from app.db.session import get_session
from app.models import CollectionItem, School, Edition
from app.permissions import Permission
from app.schemas.booklist import (
    BookListDetail
)
from app.services.collections import (
    add_editions_to_collection_by_isbn,
    get_collection_info_with_criteria,
)

logger = get_logger()

router = APIRouter(
    tags=["Booklists"],
    dependencies=[

        Security(get_current_active_user_or_service_account)
    ],
)


@router.get(
    "/lists/{wriveted_identifier}/collection",
    response_model=List[CollectionItemDetail],
)
async def get_school_collection(
    school: School = Permission("read", get_school_from_wriveted_id),
    pagination: PaginatedQueryParams = Depends(),
    session: Session = Depends(get_session),
):
    logger.debug("Getting collection", pagination=pagination)
    collection_items = session.scalars(
        school.collection.statement.offset(pagination.skip).limit(pagination.limit)
    ).all()
    logger.debug("Loading collection", collection_size=len(collection_items))
    return collection_items

