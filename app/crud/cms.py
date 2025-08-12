from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, cast, func, or_, select, text, distinct, case
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import DataError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.crud import CRUDBase
from app.models.cms import (
    CMSContent,
    CMSContentVariant,
    ContentStatus,
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
from app.schemas.analytics import FlowAnalytics

logger = get_logger()


class CRUDContent(CRUDBase[CMSContent, ContentCreate, ContentUpdate]):
    async def aget_all_with_optional_filters(
        self,
        db: AsyncSession,
        content_type: Optional[ContentType] = None,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None,
        active: Optional[bool] = None,
        status: Optional[str] = None,
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

        if status is not None:
            try:
                # Convert string to ContentStatus enum
                status_enum = ContentStatus(status)
                query = query.where(CMSContent.status == status_enum)
            except ValueError:
                logger.warning("Invalid status filter", status=status)
                # Skip invalid status filter rather than raising error

        if search is not None and len(search) > 0:
            # Case-insensitive text search within JSONB fields
            search_pattern = f"%{search.lower()}%"
            query = query.where(
                or_(
                    func.lower(cast(CMSContent.content, JSONB).op("->>")("text")).like(
                        search_pattern
                    ),
                    func.lower(cast(CMSContent.content, JSONB).op("->>")("setup")).like(
                        search_pattern
                    ),
                    func.lower(
                        cast(CMSContent.content, JSONB).op("->>")("punchline")
                    ).like(search_pattern),
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
        status: Optional[str] = None,
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

        if status is not None:
            try:
                # Convert string to ContentStatus enum
                status_enum = ContentStatus(status)
                query = query.where(CMSContent.status == status_enum)
            except ValueError:
                logger.warning("Invalid status filter", status=status)
                # Skip invalid status filter rather than raising error

        if search is not None and len(search) > 0:
            # Case-insensitive text search within JSONB fields
            search_pattern = f"%{search.lower()}%"
            query = query.where(
                or_(
                    func.lower(cast(CMSContent.content, JSONB).op("->>")("text")).like(
                        search_pattern
                    ),
                    func.lower(cast(CMSContent.content, JSONB).op("->>")("setup")).like(
                        search_pattern
                    ),
                    func.lower(
                        cast(CMSContent.content, JSONB).op("->>")("punchline")
                    ).like(search_pattern),
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
        search: Optional[str] = None,
        version: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[FlowDefinition]:
        """Get flows with filters."""
        query = self.get_all_query(db=db)

        if published is not None:
            query = query.where(FlowDefinition.is_published == published)

        if active is not None:
            query = query.where(FlowDefinition.is_active == active)

        if search is not None:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    FlowDefinition.name.ilike(search_pattern),
                    FlowDefinition.description.ilike(search_pattern),
                )
            )

        if version is not None:
            query = query.where(FlowDefinition.version == version)

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
        search: Optional[str] = None,
        version: Optional[str] = None,
    ) -> int:
        """Get count of flows with filters."""
        query = self.get_all_query(db=db)

        if published is not None:
            query = query.where(FlowDefinition.is_published == published)

        if active is not None:
            query = query.where(FlowDefinition.is_active == active)

        if search is not None:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    FlowDefinition.name.ilike(search_pattern),
                    FlowDefinition.description.ilike(search_pattern),
                )
            )

        if version is not None:
            query = query.where(FlowDefinition.version == version)

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
        """Create flow with creator and extract nodes from flow_data."""
        obj_data = obj_in.model_dump()
        if created_by:
            obj_data["created_by"] = created_by

        db_obj = FlowDefinition(**obj_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)

        # Extract nodes from flow_data and create FlowNode records
        flow_data = obj_data.get("flow_data", {})
        nodes = flow_data.get("nodes", [])

        if nodes:
            # Import here to avoid circular imports
            from app.models.cms import FlowNode, NodeType

            for node_data in nodes:
                try:
                    # Map node type from flow_data to NodeType enum
                    node_type_str = node_data.get("type", "message").upper()
                    if node_type_str == "ACTION":
                        node_type = NodeType.ACTION
                    elif node_type_str == "QUESTION":
                        node_type = NodeType.QUESTION
                    elif node_type_str == "MESSAGE":
                        node_type = NodeType.MESSAGE
                    else:
                        node_type = NodeType.MESSAGE  # default fallback

                    # Create FlowNode record
                    flow_node = FlowNode(
                        flow_id=db_obj.id,
                        node_id=node_data.get("id", ""),
                        node_type=node_type,
                        content=node_data.get("content", {}),
                        position=node_data.get("position", {"x": 0, "y": 0}),
                        info={},
                    )
                    db.add(flow_node)
                except Exception as e:
                    logger.warning(f"Failed to create FlowNode from flow_data: {e}")

            # Extract connections from flow_data and create FlowConnection records
            connections = flow_data.get("connections", [])
            if connections:
                from app.models.cms import FlowConnection, ConnectionType

                for conn_data in connections:
                    try:
                        # Map connection type from flow_data to ConnectionType enum
                        conn_type_str = conn_data.get("type", "DEFAULT").upper()
                        if conn_type_str == "DEFAULT":
                            conn_type = ConnectionType.DEFAULT
                        elif conn_type_str == "CONDITIONAL":
                            conn_type = ConnectionType.CONDITIONAL
                        else:
                            conn_type = ConnectionType.DEFAULT  # default fallback

                        flow_connection = FlowConnection(
                            flow_id=db_obj.id,
                            source_node_id=conn_data.get("source", ""),
                            target_node_id=conn_data.get("target", ""),
                            connection_type=conn_type,
                            conditions={},
                            info={},
                        )
                        db.add(flow_connection)
                    except Exception as e:
                        logger.warning(
                            f"Failed to create FlowConnection from flow_data: {e}"
                        )

            # Commit the nodes and connections
            await db.commit()

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
            # Increment version when publishing
            current_version = flow.version or "1.0.0"
            try:
                # Parse version like "1.0.0" -> [1, 0, 0] and increment minor version
                parts = current_version.split(".")
                if len(parts) >= 2:
                    minor_version = int(parts[1]) + 1
                    flow.version = f"{parts[0]}.{minor_version}.{parts[2] if len(parts) > 2 else '0'}"
                else:
                    flow.version = "1.1.0"  # Fallback
            except (ValueError, IndexError):
                flow.version = "1.1.0"  # Fallback for invalid version format
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
            # Import the schema we need
            from app.schemas.cms import FlowCreate

            # Use a select to get fresh data that avoids lazy loading issues
            from sqlalchemy import select
            from app.models.cms import FlowDefinition

            # Get a fresh copy of the source flow data with explicit loading
            stmt = select(FlowDefinition).where(FlowDefinition.id == source_flow.id)
            result = await db.execute(stmt)
            fresh_source = result.scalar_one()

            # Create new flow data - safely access fresh source attributes
            flow_data_copy = (
                dict(fresh_source.flow_data) if fresh_source.flow_data else {}
            )
            info_copy = dict(fresh_source.info) if fresh_source.info else {}

            # Create the cloned flow with original data preserved
            flow_create_schema = FlowCreate(
                name=new_name,
                description=fresh_source.description or "",
                version=new_version,
                flow_data=flow_data_copy,
                entry_node_id=fresh_source.entry_node_id or "start",
                info=info_copy,
            )

            # Use the acreate method which should work properly
            cloned_flow = await self.acreate(
                db, obj_in=flow_create_schema, created_by=created_by
            )

            # Skip nodes and connections cloning for now to avoid greenlet issues
            # TODO: Re-enable once greenlet issue is resolved
            # await self._clone_nodes_and_connections(db, source_flow.id, cloned_flow.id)
            await db.commit()

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
            # Extract values safely to avoid SQLAlchemy greenlet issues
            content_copy = dict(source_node.content) if source_node.content else {}
            position_copy = dict(source_node.position) if source_node.position else {}
            info_copy = dict(source_node.info) if source_node.info else {}

            cloned_node = FlowNode(
                flow_id=target_flow_id,
                node_id=source_node.node_id,
                node_type=source_node.node_type,
                template=source_node.template,
                content=content_copy,
                position=position_copy,
                info=info_copy,
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
            # Extract values safely to avoid SQLAlchemy greenlet issues
            conditions_copy = (
                dict(source_conn.conditions) if source_conn.conditions else {}
            )
            info_copy = dict(source_conn.info) if source_conn.info else {}

            cloned_conn = FlowConnection(
                flow_id=target_flow_id,
                source_node_id=source_conn.source_node_id,
                target_node_id=source_conn.target_node_id,
                connection_type=source_conn.connection_type,
                conditions=conditions_copy,
                info=info_copy,
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
            ).bindparams(flow_id=node.flow_id, node_id=node.node_id)
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

    async def get_flow_analytics(
        self, 
        db: AsyncSession, 
        flow_id: str, 
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ):
        """Get aggregated analytics for a specific flow."""

        
        # Set default date range if not provided
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Convert dates to datetime for comparison
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        # Query for basic session metrics
        session_stats_query = (
            select(
                func.count(distinct(ConversationSession.id)).label('total_sessions'),
                func.count(
                    case(
                        (ConversationSession.status == SessionStatus.COMPLETED, 1),
                        else_=None
                    )
                ).label('completed_sessions'),
                func.avg(
                    func.extract('epoch', ConversationSession.ended_at - ConversationSession.started_at)
                ).label('avg_duration_seconds')
            )
            .select_from(ConversationSession)
            .where(
                and_(
                    ConversationSession.flow_id == flow_id,
                    ConversationSession.started_at >= start_datetime,
                    ConversationSession.started_at <= end_datetime
                )
            )
        )
        
        session_stats = await db.execute(session_stats_query)
        stats = session_stats.first()
        
        # Calculate metrics
        total_sessions = stats.total_sessions or 0
        completed_sessions = stats.completed_sessions or 0
        completion_rate = completed_sessions / total_sessions if total_sessions > 0 else 0.0
        average_duration = stats.avg_duration_seconds or 0.0
        
        # Calculate bounce rate (sessions with only 1 interaction) 
        bounce_query = (
            select(func.count(distinct(ConversationSession.id)))
            .select_from(ConversationSession)
            .join(ConversationHistory)
            .where(
                and_(
                    ConversationSession.flow_id == flow_id,
                    ConversationSession.started_at >= start_datetime,
                    ConversationSession.started_at <= end_datetime
                )
            )
            .group_by(ConversationSession.id)
            .having(func.count(ConversationHistory.id) == 1)
        )
        
        bounce_result = await db.execute(select(func.count()).select_from(bounce_query.subquery()))
        bounce_sessions = bounce_result.scalar() or 0
        bounce_rate = bounce_sessions / total_sessions if total_sessions > 0 else 0.0
        
        # Calculate engagement metrics
        engagement_query = (
            select(
                func.count(ConversationHistory.id).label('total_interactions'),
                func.count(distinct(ConversationHistory.node_id)).label('unique_nodes_visited')
            )
            .select_from(ConversationHistory)
            .join(ConversationSession)
            .where(
                and_(
                    ConversationSession.flow_id == flow_id,
                    ConversationSession.started_at >= start_datetime,
                    ConversationSession.started_at <= end_datetime
                )
            )
        )
        
        engagement_result = await db.execute(engagement_query)
        engagement = engagement_result.first()
        
        engagement_metrics = {
            'total_interactions': engagement.total_interactions or 0,
            'unique_nodes_visited': engagement.unique_nodes_visited or 0,
            'avg_interactions_per_session': (engagement.total_interactions or 0) / total_sessions if total_sessions > 0 else 0.0
        }
        
        return FlowAnalytics(
            flow_id=flow_id,
            total_sessions=total_sessions,
            completion_rate=completion_rate,
            average_duration=average_duration,
            bounce_rate=bounce_rate,
            engagement_metrics=engagement_metrics,
            time_period={
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            }
        )

    async def get_node_analytics(
        self, 
        db: AsyncSession, 
        flow_id: str, 
        node_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ):
        """Get analytics for a specific node in a flow."""
        from datetime import timedelta
        from app.schemas.analytics import NodeAnalytics
        
        # Set default date range if not provided
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Convert dates to datetime for comparison
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        # Query for node-specific metrics
        node_stats_query = (
            select(
                func.count(ConversationHistory.id).label('total_visits'),
                func.count(
                    case(
                        (ConversationHistory.interaction_type.in_([
                            InteractionType.INPUT,
                            InteractionType.ACTION
                        ]), 1),
                        else_=None
                    )
                ).label('interactions'),
                func.count(distinct(ConversationHistory.session_id)).label('unique_sessions')
            )
            .select_from(ConversationHistory)
            .join(ConversationSession)
            .where(
                and_(
                    ConversationSession.flow_id == flow_id,
                    ConversationHistory.node_id == node_id,
                    ConversationSession.started_at >= start_datetime,
                    ConversationSession.started_at <= end_datetime
                )
            )
        )
        
        node_stats = await db.execute(node_stats_query)
        stats = node_stats.first()
        
        visits = stats.total_visits or 0
        interactions = stats.interactions or 0
        unique_sessions = stats.unique_sessions or 0
        
        # Calculate bounce rate (sessions with only 1 interaction at this node)
        bounce_rate = 0.0
        if unique_sessions > 0:
            bounce_rate = 1.0 - (interactions / visits) if visits > 0 else 0.0
        
        # Calculate proper average time spent using actual timestamps
        avg_time_seconds = await self._calculate_average_time_spent(
            db, flow_id, node_id, start_datetime, end_datetime
        )
        
        # Calculate proper response distribution from ConversationHistory content
        response_distribution = await self._calculate_response_distribution(
            db, flow_id, node_id, start_datetime, end_datetime
        )
        
        return NodeAnalytics(
            node_id=node_id,
            visits=visits,
            interactions=interactions,
            bounce_rate=bounce_rate,
            average_time_spent=avg_time_seconds,
            response_distribution=response_distribution
        )

    async def _calculate_average_time_spent(
        self, 
        db: AsyncSession, 
        flow_id: str, 
        node_id: str, 
        start_datetime: datetime, 
        end_datetime: datetime
    ) -> float:
        """Calculate average time spent on a node using actual conversation timestamps."""
        
        # Query for sequential interactions to calculate time differences
        time_query = (
            select(
                ConversationHistory.session_id,
                ConversationHistory.created_at,
                func.lead(ConversationHistory.created_at).over(
                    partition_by=ConversationHistory.session_id,
                    order_by=ConversationHistory.created_at
                ).label('next_interaction_time')
            )
            .select_from(ConversationHistory)
            .join(ConversationSession)
            .where(
                and_(
                    ConversationSession.flow_id == flow_id,
                    ConversationHistory.node_id == node_id,
                    ConversationSession.started_at >= start_datetime,
                    ConversationSession.started_at <= end_datetime
                )
            )
            .order_by(ConversationHistory.session_id, ConversationHistory.created_at)
        )
        
        try:
            time_results = await db.execute(time_query)
            time_data = time_results.all()
            
            if not time_data:
                return 0.0
            
            # Calculate time differences between this node and next interaction
            time_diffs = []
            for row in time_data:
                if row.next_interaction_time:
                    # Calculate seconds between interactions
                    time_diff = (row.next_interaction_time - row.created_at).total_seconds()
                    # Cap at reasonable maximum (10 minutes) to avoid outliers
                    if 0 < time_diff <= 600:  # 10 minutes max
                        time_diffs.append(time_diff)
            
            if time_diffs:
                return sum(time_diffs) / len(time_diffs)
            else:
                return 0.0
                
        except Exception as e:
            # Fallback to 0.0 if time calculation fails
            logger.warning(f"Error calculating average time spent: {e}")
            return 0.0

    async def _calculate_response_distribution(
        self, 
        db: AsyncSession, 
        flow_id: str, 
        node_id: str, 
        start_datetime: datetime, 
        end_datetime: datetime
    ) -> Dict[str, Any]:
        """Calculate response distribution by analyzing ConversationHistory content."""
        
        # Query for interaction content at this node
        content_query = (
            select(
                ConversationHistory.content,
                ConversationHistory.interaction_type
            )
            .select_from(ConversationHistory)
            .join(ConversationSession)
            .where(
                and_(
                    ConversationSession.flow_id == flow_id,
                    ConversationHistory.node_id == node_id,
                    ConversationSession.started_at >= start_datetime,
                    ConversationSession.started_at <= end_datetime,
                    ConversationHistory.interaction_type.in_([
                        InteractionType.INPUT,
                        InteractionType.ACTION
                    ])
                )
            )
        )
        
        try:
            content_results = await db.execute(content_query)
            content_data = content_results.all()
            
            if not content_data:
                return {}
            
            response_counts = {}
            
            for row in content_data:
                content = row.content or {}
                interaction_type = row.interaction_type
                
                # Analyze different types of responses
                if interaction_type == InteractionType.ACTION:
                    # Button clicks or actions
                    action_value = content.get('action', content.get('value', 'unknown_action'))
                    key = f"action_{action_value}"
                    response_counts[key] = response_counts.get(key, 0) + 1
                
                elif interaction_type == InteractionType.INPUT:
                    # Text input or other user inputs
                    input_value = content.get('input', content.get('text', content.get('value')))
                    if input_value:
                        # For text inputs, categorize by length or content type
                        if isinstance(input_value, str):
                            if len(input_value) <= 10:
                                key = 'short_text_input'
                            elif len(input_value) <= 50:
                                key = 'medium_text_input'
                            else:
                                key = 'long_text_input'
                        else:
                            key = 'structured_input'
                        response_counts[key] = response_counts.get(key, 0) + 1
                    else:
                        response_counts['empty_input'] = response_counts.get('empty_input', 0) + 1
                
                # If we can't categorize, count as general interaction
                if not any(key.startswith(('action_', 'short_', 'medium_', 'long_', 'structured_', 'empty_')) 
                          for key in response_counts.keys()):
                    response_counts['other_interaction'] = response_counts.get('other_interaction', 0) + 1
            
            return response_counts
            
        except Exception as e:
            # Fallback to empty distribution if analysis fails
            logger.warning(f"Error calculating response distribution: {e}")
            return {}


# Create CRUD instances
content = CRUDContent(CMSContent)
content_variant = CRUDContentVariant(CMSContentVariant)
flow = CRUDFlow(FlowDefinition)
flow_node = CRUDFlowNode(FlowNode)
flow_connection = CRUDFlowConnection(FlowConnection)
conversation_session = CRUDConversationSession(ConversationSession)
conversation_history = CRUDConversationHistory(ConversationHistory)
conversation_analytics = CRUDConversationAnalytics(ConversationAnalytics)
