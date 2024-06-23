from typing import Any

from sqlalchemy import cast, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import DataError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from structlog import get_logger

from app.crud import CRUDBase
from app.models import CMSContent, ContentType, User

logger = get_logger()


class CRUDContent(CRUDBase[CMSContent, Any, Any]):
    def get_all_with_optional_filters_query(
        self,
        db: Session,
        content_type: ContentType | None = None,
        query_string: str | None = None,
        user: User | None = None,
        jsonpath_match: str = None,
    ):
        query = self.get_all_query(db=db)

        if content_type is not None:
            query = query.where(CMSContent.type == content_type)

        if user is not None:
            query = query.where(CMSContent.user == user)

        if jsonpath_match is not None:
            # Apply the jsonpath filter to the content field
            query = query.where(
                func.jsonb_path_match(
                    cast(CMSContent.content, JSONB), jsonpath_match
                ).is_(True)
            )

        return query

    async def aget_all_with_optional_filters(
        self,
        db: AsyncSession,
        content_type: ContentType | None = None,
        query_string: str | None = None,
        user: User | None = None,
        jsonpath_match: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ):
        optional_filters = {
            "query_string": query_string,
            "content_type": content_type,
            "user": user,
            "jsonpath_match": jsonpath_match,
        }
        logger.debug("Querying digital content", **optional_filters)

        query = self.apply_pagination(
            self.get_all_with_optional_filters_query(db=db, **optional_filters),
            skip=skip,
            limit=limit,
        )
        try:
            return (await db.scalars(query)).all()
        except (ProgrammingError, DataError) as e:
            logger.error("Error querying events", error=e, **optional_filters)
            raise ValueError("Problem filtering content")


content = CRUDContent(CMSContent)
