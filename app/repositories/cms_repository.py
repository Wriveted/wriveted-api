"""
CMS Repository - Domain-focused repository for content management.

This provides domain-specific methods for managing CMS content, flows, and nodes
instead of generic CRUD operations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from structlog import get_logger

from app.models.cms import (
    CMSContent,
    ContentStatus,
    ContentType,
    ContentVisibility,
    FlowDefinition,
)

logger = get_logger()


class CMSRepository(ABC):
    """
    Domain repository interface for CMS content management.

    This interface defines content-specific methods rather than generic CRUD,
    making content management operations clear and maintainable.
    """

    @abstractmethod
    async def find_published_flows(self, db: AsyncSession) -> List[FlowDefinition]:
        """Find all published flows available for conversations."""
        pass

    @abstractmethod
    async def get_flow_with_nodes(
        self, db: AsyncSession, flow_id: UUID
    ) -> Optional[FlowDefinition]:
        """Get a complete flow definition with all its nodes and connections."""
        pass

    @abstractmethod
    async def find_content_by_type_and_tags(
        self,
        db: AsyncSession,
        content_type: ContentType,
        tags: Optional[List[str]] = None,
        active_only: bool = True,
    ) -> List[CMSContent]:
        """Find content by type and optional tags for dynamic content loading."""
        pass

    @abstractmethod
    async def get_random_content_of_type(
        self,
        db: AsyncSession,
        content_type: ContentType,
        exclude_ids: Optional[List[UUID]] = None,
    ) -> Optional[CMSContent]:
        """Get random content of a specific type for variety in conversations."""
        pass

    @abstractmethod
    async def get_random_content(
        self,
        db: AsyncSession,
        content_type: ContentType,
        count: int = 1,
        tags: Optional[List[str]] = None,
        info_filters: Optional[Dict[str, Any]] = None,
        exclude_ids: Optional[List[UUID]] = None,
        school_id: Optional[UUID] = None,
        include_public: bool = True,
    ) -> List[CMSContent]:
        """Get N random content items with filtering and visibility control.

        Args:
            db: Database session
            content_type: Type of content to retrieve
            count: Number of random items to return
            tags: Optional list of tags to filter by (array overlap)
            info_filters: Optional dict of key:value filters on the info JSONB field
            exclude_ids: Optional list of content IDs to exclude (for deduplication)
            school_id: School ID for visibility filtering (includes school-scoped content)
            include_public: Whether to include PUBLIC visibility content (default True)

        Returns:
            List of random content items matching criteria, respecting visibility rules
        """
        pass

    @abstractmethod
    async def publish_flow(
        self,
        db: AsyncSession,
        flow_id: UUID,
        published_by_user_id: Optional[UUID],
        new_version: Optional[str] = None,
    ) -> FlowDefinition:
        """Publish a flow for use in conversations."""
        pass

    @abstractmethod
    async def unpublish_flow(self, db: AsyncSession, flow_id: UUID) -> FlowDefinition:
        """Unpublish a flow to remove it from active use."""
        pass

    # Content Management Methods
    @abstractmethod
    async def create_content(
        self, db: AsyncSession, content_data: dict, created_by: Optional[UUID] = None
    ) -> CMSContent:
        """Create new content item."""
        pass

    @abstractmethod
    async def get_content_by_id(
        self, db: AsyncSession, content_id: UUID
    ) -> Optional[CMSContent]:
        """Get content by ID."""
        pass

    @abstractmethod
    async def update_content(
        self, db: AsyncSession, content_id: UUID, update_data: dict
    ) -> CMSContent:
        """Update existing content."""
        pass

    @abstractmethod
    async def delete_content(self, db: AsyncSession, content_id: UUID) -> bool:
        """Delete content by ID."""
        pass

    @abstractmethod
    async def list_content_with_filters(
        self,
        db: AsyncSession,
        content_type: Optional[ContentType] = None,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None,
        active: Optional[bool] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[CMSContent]:
        """List content with optional filters."""
        pass

    @abstractmethod
    async def count_content_with_filters(
        self,
        db: AsyncSession,
        content_type: Optional[ContentType] = None,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None,
        active: Optional[bool] = None,
        status: Optional[str] = None,
    ) -> int:
        """Count content matching filters."""
        pass


class CMSRepositoryImpl(CMSRepository):
    """
    PostgreSQL implementation of CMSRepository.

    This provides concrete implementation while maintaining the domain interface.
    """

    async def find_published_flows(self, db: AsyncSession) -> List[FlowDefinition]:
        """Find all published flows available for conversations."""
        query = (
            select(FlowDefinition)
            .where(
                and_(
                    FlowDefinition.is_published == True,
                    FlowDefinition.is_active == True,
                )
            )
            .order_by(FlowDefinition.created_at.desc())
        )

        result = await db.execute(query)
        flows = result.scalars().all()

        logger.debug("Found published flows", count=len(flows))
        return flows

    async def get_flow_with_nodes(
        self, db: AsyncSession, flow_id: UUID
    ) -> Optional[FlowDefinition]:
        """Get a complete flow definition with all its nodes and connections."""
        query = (
            select(FlowDefinition)
            .options(
                selectinload(FlowDefinition.nodes),
                selectinload(FlowDefinition.connections),
            )
            .where(FlowDefinition.id == flow_id)
        )

        result = await db.execute(query)
        flow = result.scalar_one_or_none()

        if flow:
            logger.debug(
                "Loaded flow with components",
                flow_id=flow_id,
                nodes_count=len(flow.nodes),
                connections_count=len(flow.connections),
            )
        else:
            logger.warning("Flow not found", flow_id=flow_id)

        return flow

    async def find_content_by_type_and_tags(
        self,
        db: AsyncSession,
        content_type: ContentType,
        tags: Optional[List[str]] = None,
        active_only: bool = True,
    ) -> List[CMSContent]:
        """Find content by type and optional tags for dynamic content loading."""
        query = select(CMSContent).where(CMSContent.type == content_type)

        if active_only:
            query = query.where(CMSContent.is_active == True)

        if tags:
            # PostgreSQL array overlap operator
            query = query.where(CMSContent.tags.op("&&")(tags))

        query = query.order_by(CMSContent.created_at.desc())

        result = await db.execute(query)
        content_items = result.scalars().all()

        logger.debug(
            "Found content by type and tags",
            content_type=content_type.value,
            tags=tags,
            count=len(content_items),
        )

        return content_items

    async def get_random_content_of_type(
        self,
        db: AsyncSession,
        content_type: ContentType,
        exclude_ids: Optional[List[UUID]] = None,
    ) -> Optional[CMSContent]:
        """Get random content of a specific type for variety in conversations."""
        from sqlalchemy import func

        query = (
            select(CMSContent)
            .where(and_(CMSContent.type == content_type, CMSContent.is_active == True))
            .order_by(func.random())
            .limit(1)
        )

        if exclude_ids:
            query = query.where(~CMSContent.id.in_(exclude_ids))

        result = await db.execute(query)
        content = result.scalar_one_or_none()

        if content:
            logger.debug(
                "Selected random content",
                content_type=content_type.value,
                content_id=content.id,
            )
        else:
            logger.warning("No random content found", content_type=content_type.value)

        return content

    async def get_random_content(
        self,
        db: AsyncSession,
        content_type: ContentType,
        count: int = 1,
        tags: Optional[List[str]] = None,
        info_filters: Optional[Dict[str, Any]] = None,
        exclude_ids: Optional[List[UUID]] = None,
        school_id: Optional[UUID] = None,
        include_public: bool = True,
    ) -> List[CMSContent]:
        """Get N random content items with filtering and visibility control.

        Visibility rules:
        - WRIVETED visibility content is always included (global Wriveted content)
        - PUBLIC visibility content is included when include_public=True
        - SCHOOL and PRIVATE visibility requires matching school_id
        """
        # Start with base conditions
        conditions = [
            CMSContent.type == content_type,
            CMSContent.is_active == True,
        ]

        # Build visibility conditions
        visibility_conditions = [
            CMSContent.visibility == ContentVisibility.WRIVETED,
        ]

        if include_public:
            visibility_conditions.append(
                CMSContent.visibility == ContentVisibility.PUBLIC
            )

        if school_id:
            # Include content owned by this school (SCHOOL or PRIVATE visibility)
            visibility_conditions.append(
                and_(
                    CMSContent.school_id == school_id,
                    CMSContent.visibility.in_(
                        [ContentVisibility.SCHOOL, ContentVisibility.PRIVATE]
                    ),
                )
            )

        conditions.append(or_(*visibility_conditions))

        # Apply tag filtering (array overlap)
        if tags:
            conditions.append(CMSContent.tags.op("&&")(tags))

        # Apply info JSONB filtering
        if info_filters:
            for key, value in info_filters.items():
                # Handle numeric comparisons for age filtering
                if key in ("min_age", "max_age") and isinstance(value, (int, str)):
                    try:
                        age_value = int(value)
                        if key == "min_age":
                            # User's age should be >= content's min_age
                            # Filter: content.info.min_age <= user_age
                            conditions.append(
                                text("(info->>'min_age')::int <= :min_age").bindparams(
                                    min_age=age_value
                                )
                            )
                        elif key == "max_age":
                            # User's age should be <= content's max_age
                            # Filter: content.info.max_age >= user_age
                            conditions.append(
                                text("(info->>'max_age')::int >= :max_age").bindparams(
                                    max_age=age_value
                                )
                            )
                    except (ValueError, TypeError):
                        logger.warning(
                            "Invalid age value in info_filters",
                            key=key,
                            value=value,
                        )
                else:
                    # Use JSONB containment for other key:value matches
                    # This checks if info @> '{"key": "value"}'
                    import json

                    json_filter = json.dumps({key: value})
                    conditions.append(
                        text("info @> :json_filter::jsonb").bindparams(
                            json_filter=json_filter
                        )
                    )

        # Apply exclusion list
        if exclude_ids:
            conditions.append(~CMSContent.id.in_(exclude_ids))

        # Build query with random ordering
        query = (
            select(CMSContent)
            .where(and_(*conditions))
            .order_by(func.random())
            .limit(count)
        )

        result = await db.execute(query)
        content_items = list(result.scalars().all())

        logger.debug(
            "Selected random content",
            content_type=content_type.value,
            count=len(content_items),
            requested_count=count,
            tags=tags,
            info_filters=info_filters,
            school_id=str(school_id) if school_id else None,
        )

        return content_items

    async def publish_flow(
        self,
        db: AsyncSession,
        flow_id: UUID,
        published_by_user_id: Optional[UUID],
        new_version: Optional[str] = None,
    ) -> FlowDefinition:
        """Publish a flow for use in conversations."""
        from datetime import datetime

        query = select(FlowDefinition).where(FlowDefinition.id == flow_id)
        result = await db.execute(query)
        flow = result.scalar_one()

        flow.is_published = True
        flow.published_at = datetime.utcnow()
        flow.published_by = published_by_user_id

        # Update version if provided
        if new_version:
            flow.version = new_version

        await db.commit()
        await db.refresh(flow)

        logger.info(
            "Published flow", flow_id=flow_id, published_by=published_by_user_id
        )

        return flow

    async def unpublish_flow(self, db: AsyncSession, flow_id: UUID) -> FlowDefinition:
        """Unpublish a flow to remove it from active use."""
        query = select(FlowDefinition).where(FlowDefinition.id == flow_id)
        result = await db.execute(query)
        flow = result.scalar_one()

        flow.is_published = False
        flow.published_at = None
        flow.published_by = None

        await db.commit()
        await db.refresh(flow)

        logger.info("Unpublished flow", flow_id=flow_id)

        return flow

    # Content Management Implementation
    async def create_content(
        self, db: AsyncSession, content_data: dict, created_by: Optional[UUID] = None
    ) -> CMSContent:
        """Create new content item."""
        # Handle visibility - convert string to enum if needed
        visibility = content_data.get("visibility", ContentVisibility.WRIVETED)
        if isinstance(visibility, str):
            visibility = ContentVisibility(visibility)

        content = CMSContent(
            type=content_data["type"],
            content=content_data["content"],
            info=content_data.get("info", {}),
            tags=content_data.get("tags", []),
            is_active=content_data.get("is_active", True),
            status=content_data.get("status", ContentStatus.DRAFT),
            created_by=created_by,
            school_id=content_data.get("school_id"),
            visibility=visibility,
        )

        db.add(content)
        await db.flush()
        await db.refresh(content)

        logger.info("Created content", content_id=content.id, type=content.type)

        return content

    async def get_content_by_id(
        self, db: AsyncSession, content_id: UUID
    ) -> Optional[CMSContent]:
        """Get content by ID."""
        query = select(CMSContent).where(CMSContent.id == content_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def update_content(
        self, db: AsyncSession, content_id: UUID, update_data: dict
    ) -> CMSContent:
        """Update existing content."""
        query = select(CMSContent).where(CMSContent.id == content_id)
        result = await db.execute(query)
        content = result.scalar_one()

        # Update fields
        for field, value in update_data.items():
            if hasattr(content, field) and value is not None:
                # Convert string to enum for status, type, and visibility fields
                if field == "status" and isinstance(value, str):
                    value = ContentStatus(value)
                elif field == "type" and isinstance(value, str):
                    value = ContentType(value)
                elif field == "visibility" and isinstance(value, str):
                    value = ContentVisibility(value)
                setattr(content, field, value)

        # Increment version on content changes
        if "content" in update_data:
            content.version = content.version + 1

        await db.flush()
        await db.refresh(content)

        logger.info("Updated content", content_id=content_id)

        return content

    async def delete_content(self, db: AsyncSession, content_id: UUID) -> bool:
        """Delete content by ID."""
        query = select(CMSContent).where(CMSContent.id == content_id)
        result = await db.execute(query)
        content = result.scalar_one_or_none()

        if not content:
            return False

        await db.delete(content)
        await db.commit()

        logger.info("Deleted content", content_id=content_id)

        return True

    async def list_content_with_filters(
        self,
        db: AsyncSession,
        content_type: Optional[ContentType] = None,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None,
        active: Optional[bool] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[CMSContent]:
        """List content with optional filters."""
        query = select(CMSContent)

        # Apply filters
        conditions = []

        if content_type:
            conditions.append(CMSContent.type == content_type)

        if active is not None:
            conditions.append(CMSContent.is_active == active)

        if status:
            try:
                status_enum = ContentStatus(status)
                conditions.append(CMSContent.status == status_enum)
            except ValueError:
                logger.warning("Invalid status filter", status=status)

        if tags:
            # Use PostgreSQL array overlap operator to match any tag
            conditions.append(CMSContent.tags.op("&&")(tags))

        if search:
            # Use full-text search on generated/trigger-maintained tsvector
            fts_condition = text(
                "search_document @@ websearch_to_tsquery('english', :q)"
            ).bindparams(q=search)
            conditions.append(fts_condition)

        if conditions:
            query = query.where(and_(*conditions))

        # Order by FTS rank when searching, otherwise recency
        if search:
            order_clause = text(
                "ts_rank(search_document, websearch_to_tsquery('english', :q)) DESC, created_at DESC"
            ).bindparams(q=search)
            query = query.order_by(order_clause)
        else:
            query = query.order_by(CMSContent.created_at.desc())
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        content_items = result.scalars().all()

        logger.debug(
            "Listed content with filters",
            count=len(content_items),
            content_type=content_type,
            active=active,
            status=status,
        )

        return content_items

    async def count_content_with_filters(
        self,
        db: AsyncSession,
        content_type: Optional[ContentType] = None,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None,
        active: Optional[bool] = None,
        status: Optional[str] = None,
    ) -> int:
        """Count content matching filters."""
        query = select(func.count(CMSContent.id))

        # Apply same filters as list_content_with_filters
        conditions = []

        if content_type:
            conditions.append(CMSContent.type == content_type)

        if active is not None:
            conditions.append(CMSContent.is_active == active)

        if status:
            try:
                status_enum = ContentStatus(status)
                conditions.append(CMSContent.status == status_enum)
            except ValueError:
                logger.warning("Invalid status filter", status=status)

        if tags:
            conditions.append(CMSContent.tags.op("&&")(tags))

        if search:
            fts_condition = text(
                "search_document @@ websearch_to_tsquery('english', :q)"
            ).bindparams(q=search)
            conditions.append(fts_condition)

        if conditions:
            query = query.where(and_(*conditions))

        result = await db.execute(query)
        count = result.scalar()

        logger.debug("Counted content with filters", count=count)

        return count
