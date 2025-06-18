from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, cast, func, or_, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import DataError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.crud import CRUDBase
from app.models.cms import (
    CMSContent,
    CMSContentVariant,
    ContentType,
    ConversationAnalytics,
    ConversationHistory,
    ConversationSession,
    FlowConnection,
    FlowDefinition,
    FlowNode,
    InteractionType,
    SessionStatus,
)
from app.schemas.cms import (
    ConnectionCreate,
    ContentCreate,
    ContentUpdate,
    ContentVariantCreate,
    ContentVariantUpdate,
    FlowCreate,
    FlowUpdate,
    InteractionCreate,
    NodeCreate,
    NodeUpdate,
    SessionCreate,
)

logger = get_logger()


class CRUDContent(CRUDBase[CMSContent, ContentCreate, ContentUpdate]):
    async def aget_all_with_optional_filters(
        self,
        db: AsyncSession,
        content_type: Optional[ContentType] = None,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None,
        active: Optional[bool] = None,
        jsonpath_match: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[CMSContent]:
        """Get content with various filters."""
        query = self.get_all_query(db=db)

        if content_type is not None:
            query = query.where(CMSContent.type == content_type)

        if tags is not None and len(tags) > 0:
            # PostgreSQL array overlap operator
            query = query.where(CMSContent.tags.op("&&")(tags))

        if active is not None:
            query = query.where(CMSContent.is_active == active)

        if search is not None and len(search) > 0:
            # Full-text search on content JSONB field using contains operator
            query = query.where(
                or_(
                    cast(CMSContent.content, JSONB).op("@>")(
                        func.jsonb_build_object("text", search)
                    ),
                    cast(CMSContent.content, JSONB).op("@>")(
                        func.jsonb_build_object("setup", search)
                    ),
                    cast(CMSContent.content, JSONB).op("@>")(
                        func.jsonb_build_object("punchline", search)
                    ),
                )
            )

        if jsonpath_match is not None:
            try:
                query = query.where(
                    func.jsonb_path_match(
                        cast(CMSContent.content, JSONB), jsonpath_match
                    ).is_(True)
                )
            except (ProgrammingError, DataError) as e:
                logger.error(
                    "Error with JSONPath filter", error=e, jsonpath=jsonpath_match
                )
                raise ValueError("Invalid JSONPath expression")

        query = self.apply_pagination(query, skip=skip, limit=limit)

        try:
            result = await db.scalars(query)
            return result.all()
        except (ProgrammingError, DataError) as e:
            logger.error("Error querying content", error=e)
            raise ValueError("Problem filtering content")

    async def aget_count_with_optional_filters(
        self,
        db: AsyncSession,
        content_type: Optional[ContentType] = None,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None,
        active: Optional[bool] = None,
        jsonpath_match: Optional[str] = None,
    ) -> int:
        """Get count of content with filters."""
        query = self.get_all_query(db=db)

        if content_type is not None:
            query = query.where(CMSContent.type == content_type)

        if tags is not None and len(tags) > 0:
            query = query.where(CMSContent.tags.op("&&")(tags))

        if active is not None:
            query = query.where(CMSContent.is_active == active)

        if search is not None:
            query = query.where(
                or_(
                    cast(CMSContent.content, JSONB).op("@>")(
                        func.jsonb_build_object("text", search)
                    ),
                    cast(CMSContent.content, JSONB).op("@>")(
                        func.jsonb_build_object("setup", search)
                    ),
                    cast(CMSContent.content, JSONB).op("@>")(
                        func.jsonb_build_object("punchline", search)
                    ),
                )
            )

        if jsonpath_match is not None:
            try:
                query = query.where(
                    func.jsonb_path_match(
                        cast(CMSContent.content, JSONB), jsonpath_match
                    ).is_(True)
                )
            except (ProgrammingError, DataError) as e:
                logger.error(
                    "Error with JSONPath filter", error=e, jsonpath=jsonpath_match
                )
                raise ValueError("Invalid JSONPath expression")

        try:
            # Create a proper count query from the subquery
            subquery = query.subquery()
            count_query = select(func.count()).select_from(subquery)
            result = await db.scalar(count_query)
            return result or 0
        except (ProgrammingError, DataError) as e:
            logger.error("Error counting content", error=e)
            raise ValueError("Problem counting content")

    async def acreate(
        self,
        db: AsyncSession,
        *,
        obj_in: ContentCreate,
        created_by: Optional[UUID] = None,
    ) -> CMSContent:
        """Create content with creator."""
        obj_data = obj_in.model_dump()
        if created_by:
            obj_data["created_by"] = created_by

        db_obj = CMSContent(**obj_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj


class CRUDContentVariant(
    CRUDBase[CMSContentVariant, ContentVariantCreate, ContentVariantUpdate]
):
    async def aget_by_content_id(
        self,
        db: AsyncSession,
        *,
        content_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> List[CMSContentVariant]:
        """Get variants for specific content."""
        query = (
            self.get_all_query(db=db)
            .where(CMSContentVariant.content_id == content_id)
            .order_by(CMSContentVariant.created_at.desc())
        )
        query = self.apply_pagination(query, skip=skip, limit=limit)

        result = await db.scalars(query)
        return result.all()

    async def aget_count_by_content_id(
        self, db: AsyncSession, *, content_id: UUID
    ) -> int:
        """Get count of variants for specific content."""
        query = self.get_all_query(db=db).where(
            CMSContentVariant.content_id == content_id
        )

        try:
            subquery = query.subquery()
            count_query = select(func.count()).select_from(subquery)
            result = await db.scalar(count_query)
            return result or 0
        except (ProgrammingError, DataError) as e:
            logger.error("Error counting content variants", error=e)
            raise ValueError("Problem counting content variants")

    async def acreate(
        self, db: AsyncSession, *, obj_in: ContentVariantCreate, content_id: UUID
    ) -> CMSContentVariant:
        """Create content variant."""
        obj_data = obj_in.model_dump()
        obj_data["content_id"] = content_id

        db_obj = CMSContentVariant(**obj_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def aupdate_performance(
        self, db: AsyncSession, *, variant_id: UUID, performance_data: Dict[str, Any]
    ) -> CMSContentVariant:
        """Update performance data for a variant."""
        variant = await self.aget(db, variant_id)
        if not variant:
            raise ValueError("Variant not found")

        # Merge with existing performance data
        current_data = variant.performance_data or {}
        current_data.update(performance_data)
        variant.performance_data = current_data

        await db.commit()
        await db.refresh(variant)
        return variant


class CRUDFlow(CRUDBase[FlowDefinition, FlowCreate, FlowUpdate]):
    async def aget_all_with_filters(
        self,
        db: AsyncSession,
        *,
        published: Optional[bool] = None,
        active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[FlowDefinition]:
        """Get flows with filters."""
        query = self.get_all_query(db=db)

        if published is not None:
            query = query.where(FlowDefinition.is_published == published)

        if active is not None:
            query = query.where(FlowDefinition.is_active == active)

        query = query.order_by(FlowDefinition.updated_at.desc())
        query = self.apply_pagination(query, skip=skip, limit=limit)

        result = await db.scalars(query)
        return result.all()

    async def aget_count_with_filters(
        self,
        db: AsyncSession,
        *,
        published: Optional[bool] = None,
        active: Optional[bool] = None,
    ) -> int:
        """Get count of flows with filters."""
        query = self.get_all_query(db=db)

        if published is not None:
            query = query.where(FlowDefinition.is_published == published)

        if active is not None:
            query = query.where(FlowDefinition.is_active == active)

        try:
            subquery = query.subquery()
            count_query = select(func.count()).select_from(subquery)
            result = await db.scalar(count_query)
            return result or 0
        except (ProgrammingError, DataError) as e:
            logger.error("Error counting flows", error=e)
            raise ValueError("Problem counting flows")

    async def acreate(
        self, db: AsyncSession, *, obj_in: FlowCreate, created_by: Optional[UUID] = None
    ) -> FlowDefinition:
        """Create flow with creator."""
        obj_data = obj_in.model_dump()
        if created_by:
            obj_data["created_by"] = created_by

        db_obj = FlowDefinition(**obj_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def aupdate_publish_status(
        self,
        db: AsyncSession,
        *,
        flow_id: UUID,
        published: bool,
        published_by: Optional[UUID] = None,
    ) -> FlowDefinition:
        """Update flow publish status."""
        flow = await self.aget(db, flow_id)
        if not flow:
            raise ValueError("Flow not found")

        flow.is_published = published
        if published:
            flow.published_at = datetime.utcnow()
            if published_by:
                flow.published_by = published_by
        else:
            flow.published_at = None
            flow.published_by = None

        await db.commit()
        await db.refresh(flow)
        return flow

    async def aclone(
        self,
        db: AsyncSession,
        *,
        source_flow: FlowDefinition,
        new_name: str,
        new_version: str,
        created_by: Optional[UUID] = None,
    ) -> FlowDefinition:
        """Clone an existing flow with transaction safety."""
        try:
            # Create new flow with copied data
            cloned_flow = FlowDefinition(
                name=new_name,
                description=source_flow.description,
                version=new_version,
                flow_data=source_flow.flow_data.copy(),
                entry_node_id=source_flow.entry_node_id,
                info=source_flow.info.copy(),
                created_by=created_by,
                is_published=False,
                is_active=True,
            )

            db.add(cloned_flow)
            await db.flush()  # Get the ID without committing

            # Clone nodes and connections within the same transaction
            await self._clone_nodes_and_connections(db, source_flow.id, cloned_flow.id)

            # Commit everything together
            await db.commit()
            await db.refresh(cloned_flow)

            return cloned_flow
        except Exception as e:
            await db.rollback()
            logger.error(
                "Error during flow cloning",
                source_flow_id=source_flow.id,
                new_name=new_name,
                error=str(e),
            )
            raise ValueError(f"Failed to clone flow: {str(e)}")

    async def _clone_nodes_and_connections(
        self, db: AsyncSession, source_flow_id: UUID, target_flow_id: UUID
    ):
        """Helper to clone nodes and connections within an existing transaction."""
        # Get source nodes
        source_nodes = await db.scalars(
            self.get_all_query(db=db, model=FlowNode).where(
                FlowNode.flow_id == source_flow_id
            )
        )

        # Clone nodes
        node_mapping = {}  # source_node_id -> cloned_node
        for source_node in source_nodes.all():
            cloned_node = FlowNode(
                flow_id=target_flow_id,
                node_id=source_node.node_id,
                node_type=source_node.node_type,
                template=source_node.template,
                content=source_node.content.copy(),
                position=source_node.position.copy(),
                metadata=source_node.meta_data.copy(),
            )
            db.add(cloned_node)
            node_mapping[source_node.node_id] = cloned_node

        # Flush to get node IDs for relationship validation
        await db.flush()

        # Get source connections
        source_connections = await db.scalars(
            self.get_all_query(db=db, model=FlowConnection).where(
                FlowConnection.flow_id == source_flow_id
            )
        )

        # Clone connections
        for source_conn in source_connections.all():
            cloned_conn = FlowConnection(
                flow_id=target_flow_id,
                source_node_id=source_conn.source_node_id,
                target_node_id=source_conn.target_node_id,
                connection_type=source_conn.connection_type,
                conditions=source_conn.conditions.copy(),
                metadata=source_conn.meta_data.copy(),
            )
            db.add(cloned_conn)

        # No commit here - caller will handle transaction commit/rollback


class CRUDFlowNode(CRUDBase[FlowNode, NodeCreate, NodeUpdate]):
    async def aget_by_flow_id(
        self,
        db: AsyncSession,
        *,
        flow_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> List[FlowNode]:
        """Get nodes for specific flow."""
        query = (
            self.get_all_query(db=db)
            .where(FlowNode.flow_id == flow_id)
            .order_by(FlowNode.created_at)
        )
        query = self.apply_pagination(query, skip=skip, limit=limit)

        result = await db.scalars(query)
        return result.all()

    async def aget_count_by_flow_id(self, db: AsyncSession, *, flow_id: UUID) -> int:
        """Get count of nodes for specific flow."""
        query = self.get_all_query(db=db).where(FlowNode.flow_id == flow_id)

        try:
            subquery = query.subquery()
            count_query = select(func.count()).select_from(subquery)
            result = await db.scalar(count_query)
            return result or 0
        except (ProgrammingError, DataError) as e:
            logger.error("Error counting flow nodes", error=e)
            raise ValueError("Problem counting flow nodes")

    async def aget_by_flow_and_node_id(
        self, db: AsyncSession, *, flow_id: UUID, node_id: str
    ) -> Optional[FlowNode]:
        """Get specific node by flow and node ID."""
        result = await db.scalars(
            self.get_all_query(db=db).where(
                and_(FlowNode.flow_id == flow_id, FlowNode.node_id == node_id)
            )
        )
        return result.first()

    async def acreate(
        self, db: AsyncSession, *, obj_in: NodeCreate, flow_id: UUID
    ) -> FlowNode:
        """Create flow node."""
        obj_data = obj_in.model_dump()
        obj_data["flow_id"] = flow_id

        db_obj = FlowNode(**obj_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def aremove_with_connections(self, db: AsyncSession, *, node: FlowNode):
        """Remove node and all its connections."""
        # Delete connections first
        await db.execute(
            text(
                "DELETE FROM flow_connections WHERE flow_id = :flow_id AND (source_node_id = :node_id OR target_node_id = :node_id)"
            ).bindparam(flow_id=node.flow_id, node_id=node.node_id)
        )

        # Delete the node
        await db.delete(node)
        await db.commit()

    async def aupdate_positions(
        self, db: AsyncSession, *, flow_id: UUID, positions: Dict[str, Dict[str, Any]]
    ):
        """Batch update node positions."""
        for node_id, position in positions.items():
            result = await db.scalars(
                self.get_all_query(db=db).where(
                    and_(FlowNode.flow_id == flow_id, FlowNode.node_id == node_id)
                )
            )
            node = result.first()
            if node:
                node.position = position

        await db.commit()


class CRUDFlowConnection(CRUDBase[FlowConnection, ConnectionCreate, Any]):
    async def aget_by_flow_id(
        self,
        db: AsyncSession,
        *,
        flow_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> List[FlowConnection]:
        """Get connections for specific flow."""
        query = (
            self.get_all_query(db=db)
            .where(FlowConnection.flow_id == flow_id)
            .order_by(FlowConnection.created_at)
        )
        query = self.apply_pagination(query, skip=skip, limit=limit)

        result = await db.scalars(query)
        return result.all()

    async def aget_count_by_flow_id(self, db: AsyncSession, *, flow_id: UUID) -> int:
        """Get count of connections for specific flow."""
        query = self.get_all_query(db=db).where(FlowConnection.flow_id == flow_id)

        try:
            subquery = query.subquery()
            count_query = select(func.count()).select_from(subquery)
            result = await db.scalar(count_query)
            return result or 0
        except (ProgrammingError, DataError) as e:
            logger.error("Error counting flow connections", error=e)
            raise ValueError("Problem counting flow connections")

    async def acreate(
        self, db: AsyncSession, *, obj_in: ConnectionCreate, flow_id: UUID
    ) -> FlowConnection:
        """Create flow connection."""
        obj_data = obj_in.model_dump()
        obj_data["flow_id"] = flow_id

        db_obj = FlowConnection(**obj_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj


class CRUDConversationSession(CRUDBase[ConversationSession, SessionCreate, Any]):
    async def aget_by_token(
        self, db: AsyncSession, *, session_token: str
    ) -> Optional[ConversationSession]:
        """Get session by token."""
        result = await db.scalars(
            self.get_all_query(db=db).where(
                ConversationSession.session_token == session_token
            )
        )
        return result.first()

    async def aget_by_user(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
        status: Optional[SessionStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ConversationSession]:
        """Get sessions for specific user."""
        query = self.get_all_query(db=db).where(ConversationSession.user_id == user_id)

        if status:
            query = query.where(ConversationSession.status == status)

        query = query.order_by(ConversationSession.started_at.desc())
        query = self.apply_pagination(query, skip=skip, limit=limit)

        result = await db.scalars(query)
        return result.all()

    async def acreate_with_token(
        self, db: AsyncSession, *, obj_in: SessionCreate, session_token: str
    ) -> ConversationSession:
        """Create session with generated token."""
        obj_data = obj_in.model_dump()
        obj_data["session_token"] = session_token

        db_obj = ConversationSession(**obj_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def aupdate_activity(
        self,
        db: AsyncSession,
        *,
        session_id: UUID,
        current_node_id: Optional[str] = None,
    ) -> ConversationSession:
        """Update session activity timestamp and current node."""
        session = await self.aget(db, session_id)
        if not session:
            raise ValueError("Session not found")

        session.last_activity_at = datetime.utcnow()
        if current_node_id:
            session.current_node_id = current_node_id

        await db.commit()
        await db.refresh(session)
        return session

    async def aend_session(
        self,
        db: AsyncSession,
        *,
        session_id: UUID,
        status: SessionStatus = SessionStatus.COMPLETED,
    ) -> ConversationSession:
        """End a session."""
        session = await self.aget(db, session_id)
        if not session:
            raise ValueError("Session not found")

        session.status = status
        session.ended_at = datetime.utcnow()

        await db.commit()
        await db.refresh(session)
        return session


class CRUDConversationHistory(CRUDBase[ConversationHistory, InteractionCreate, Any]):
    async def aget_by_session(
        self,
        db: AsyncSession,
        *,
        session_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ConversationHistory]:
        """Get conversation history for session."""
        query = (
            self.get_all_query(db=db)
            .where(ConversationHistory.session_id == session_id)
            .order_by(ConversationHistory.created_at)
        )
        query = self.apply_pagination(query, skip=skip, limit=limit)

        result = await db.scalars(query)
        return result.all()

    async def acreate_interaction(
        self,
        db: AsyncSession,
        *,
        session_id: UUID,
        node_id: str,
        interaction_type: InteractionType,
        content: Dict[str, Any],
    ) -> ConversationHistory:
        """Create interaction history entry."""
        db_obj = ConversationHistory(
            session_id=session_id,
            node_id=node_id,
            interaction_type=interaction_type,
            content=content,
        )

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj


class CRUDConversationAnalytics(CRUDBase[ConversationAnalytics, Any, Any]):
    async def aget_by_flow(
        self,
        db: AsyncSession,
        *,
        flow_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        node_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ConversationAnalytics]:
        """Get analytics for flow."""
        query = self.get_all_query(db=db).where(
            ConversationAnalytics.flow_id == flow_id
        )

        if start_date:
            query = query.where(ConversationAnalytics.date >= start_date)
        if end_date:
            query = query.where(ConversationAnalytics.date <= end_date)
        if node_id:
            query = query.where(ConversationAnalytics.node_id == node_id)

        query = query.order_by(ConversationAnalytics.date.desc())
        query = self.apply_pagination(query, skip=skip, limit=limit)

        result = await db.scalars(query)
        return result.all()

    async def aupsert_metrics(
        self,
        db: AsyncSession,
        *,
        flow_id: UUID,
        node_id: Optional[str],
        date: date,
        metrics: Dict[str, Any],
    ) -> ConversationAnalytics:
        """Upsert analytics metrics."""
        # Try to find existing record
        existing = await db.scalars(
            self.get_all_query(db=db).where(
                and_(
                    ConversationAnalytics.flow_id == flow_id,
                    ConversationAnalytics.node_id == node_id,
                    ConversationAnalytics.date == date,
                )
            )
        )

        record = existing.first()
        if record:
            # Update existing metrics
            current_metrics = record.metrics or {}
            current_metrics.update(metrics)
            record.metrics = current_metrics
        else:
            # Create new record
            record = ConversationAnalytics(
                flow_id=flow_id, node_id=node_id, date=date, metrics=metrics
            )
            db.add(record)

        await db.commit()
        await db.refresh(record)
        return record


# Create CRUD instances
content = CRUDContent(CMSContent)
content_variant = CRUDContentVariant(CMSContentVariant)
flow = CRUDFlow(FlowDefinition)
flow_node = CRUDFlowNode(FlowNode)
flow_connection = CRUDFlowConnection(FlowConnection)
conversation_session = CRUDConversationSession(ConversationSession)
conversation_history = CRUDConversationHistory(ConversationHistory)
conversation_analytics = CRUDConversationAnalytics(ConversationAnalytics)
