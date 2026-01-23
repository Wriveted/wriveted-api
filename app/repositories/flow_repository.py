"""
Flow Repository - Domain-focused repository for flow management.

This provides domain-specific methods for managing flows, nodes, and connections
instead of generic CRUD operations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from structlog import get_logger

from app.models.cms import FlowConnection, FlowDefinition, FlowNode
from app.schemas.cms import (
    ConnectionCreate,
    FlowCreate,
    FlowUpdate,
    NodeCreate,
    NodeUpdate,
)

logger = get_logger()


class FlowRepository(ABC):
    """
    Domain repository interface for flow management.

    This interface defines flow-specific methods rather than generic CRUD,
    making flow management operations clear and maintainable.
    """

    # Flow Management Methods
    @abstractmethod
    async def find_flows_with_filters(
        self,
        db: AsyncSession,
        published: Optional[bool] = None,
        active: Optional[bool] = None,
        search: Optional[str] = None,
        version: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[FlowDefinition]:
        """Find flows with optional filters for listing operations."""
        pass

    @abstractmethod
    async def count_flows_with_filters(
        self,
        db: AsyncSession,
        published: Optional[bool] = None,
        active: Optional[bool] = None,
        search: Optional[str] = None,
        version: Optional[str] = None,
    ) -> int:
        """Count flows matching filters."""
        pass

    @abstractmethod
    async def get_flow_by_id(
        self, db: AsyncSession, flow_id: UUID
    ) -> Optional[FlowDefinition]:
        """Get flow by ID."""
        pass

    @abstractmethod
    async def get_flow_with_components(
        self, db: AsyncSession, flow_id: UUID
    ) -> Optional[FlowDefinition]:
        """Get a complete flow definition with all its nodes and connections."""
        pass

    @abstractmethod
    async def create_flow(
        self, db: AsyncSession, flow_data: FlowCreate, created_by: Optional[UUID] = None
    ) -> FlowDefinition:
        """Create new flow."""
        pass

    @abstractmethod
    async def update_flow(
        self, db: AsyncSession, flow_id: UUID, update_data: FlowUpdate
    ) -> FlowDefinition:
        """Update existing flow."""
        pass

    @abstractmethod
    async def clone_flow(
        self,
        db: AsyncSession,
        source_flow: FlowDefinition,
        new_name: str,
        created_by: Optional[UUID] = None,
        new_description: Optional[str] = None,
        version: Optional[str] = None,
        info_override: Optional[Dict[str, Any]] = None,
        clone_nodes: bool = True,
        clone_connections: bool = True,
    ) -> FlowDefinition:
        """Clone an existing flow with all its nodes and connections."""
        pass

    @abstractmethod
    async def publish_flow(
        self,
        db: AsyncSession,
        flow_id: UUID,
        published_by_user_id: Optional[UUID],
        version: Optional[str] = None,
    ) -> FlowDefinition:
        """Publish a flow for use in conversations."""
        pass

    @abstractmethod
    async def unpublish_flow(self, db: AsyncSession, flow_id: UUID) -> FlowDefinition:
        """Unpublish a flow to remove it from active use."""
        pass

    @abstractmethod
    async def soft_delete_flow(self, db: AsyncSession, flow_id: UUID) -> FlowDefinition:
        """Soft delete flow by setting is_active=False."""
        pass

    # Node Management Methods
    @abstractmethod
    async def get_nodes_by_flow(
        self, db: AsyncSession, flow_id: UUID
    ) -> List[FlowNode]:
        """Get all nodes for a specific flow."""
        pass

    @abstractmethod
    async def create_node(
        self, db: AsyncSession, flow_id: UUID, node_data: NodeCreate
    ) -> FlowNode:
        """Create new node in flow."""
        pass

    @abstractmethod
    async def update_node(
        self, db: AsyncSession, node_id: UUID, update_data: NodeUpdate
    ) -> FlowNode:
        """Update existing node."""
        pass

    @abstractmethod
    async def delete_node_with_connections(
        self, db: AsyncSession, node_id: UUID
    ) -> bool:
        """Delete node and all its connections."""
        pass

    # Connection Management Methods
    @abstractmethod
    async def get_connections_by_flow(
        self, db: AsyncSession, flow_id: UUID
    ) -> List[FlowConnection]:
        """Get all connections for a specific flow."""
        pass

    @abstractmethod
    async def create_connection(
        self, db: AsyncSession, flow_id: UUID, connection_data: ConnectionCreate
    ) -> FlowConnection:
        """Create new connection in flow."""
        pass

    @abstractmethod
    async def delete_connection(self, db: AsyncSession, connection_id: UUID) -> bool:
        """Delete connection by ID."""
        pass


class FlowRepositoryImpl(FlowRepository):
    """
    PostgreSQL implementation of FlowRepository.

    This provides concrete implementation while maintaining the domain interface.
    """

    async def find_flows_with_filters(
        self,
        db: AsyncSession,
        published: Optional[bool] = None,
        active: Optional[bool] = None,
        search: Optional[str] = None,
        version: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[FlowDefinition]:
        """Find flows with optional filters for listing operations."""
        query = select(FlowDefinition)

        conditions = []
        if published is not None:
            conditions.append(FlowDefinition.is_published == published)
        if active is not None:
            conditions.append(FlowDefinition.is_active == active)
        if search:
            conditions.append(func.lower(FlowDefinition.name).contains(search.lower()))
        if version:
            conditions.append(FlowDefinition.version == version)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(FlowDefinition.created_at.desc())
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        flows = result.scalars().all()

        logger.debug(
            "Found flows with filters",
            count=len(flows),
            published=published,
            active=active,
            search=search,
        )

        return flows

    async def count_flows_with_filters(
        self,
        db: AsyncSession,
        published: Optional[bool] = None,
        active: Optional[bool] = None,
        search: Optional[str] = None,
        version: Optional[str] = None,
    ) -> int:
        """Count flows matching filters."""
        query = select(func.count(FlowDefinition.id))

        conditions = []
        if published is not None:
            conditions.append(FlowDefinition.is_published == published)
        if active is not None:
            conditions.append(FlowDefinition.is_active == active)
        if search:
            conditions.append(func.lower(FlowDefinition.name).contains(search.lower()))
        if version:
            conditions.append(FlowDefinition.version == version)

        if conditions:
            query = query.where(and_(*conditions))

        result = await db.execute(query)
        count = result.scalar()

        logger.debug("Counted flows with filters", count=count)

        return count

    async def get_flow_by_id(
        self, db: AsyncSession, flow_id: UUID
    ) -> Optional[FlowDefinition]:
        """Get flow by ID."""
        query = select(FlowDefinition).where(FlowDefinition.id == flow_id)
        result = await db.execute(query)
        flow = result.scalar_one_or_none()

        if flow:
            logger.debug("Found flow by ID", flow_id=flow_id)
        else:
            logger.debug("Flow not found", flow_id=flow_id)

        return flow

    async def get_flow_with_components(
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

    async def create_flow(
        self, db: AsyncSession, flow_data: FlowCreate, created_by: Optional[UUID] = None
    ) -> FlowDefinition:
        """Create new flow."""
        # Create the base flow record
        info_payload = flow_data.info or {}
        if flow_data.contract is not None:
            info_payload = {
                **info_payload,
                "contract": flow_data.contract.model_dump(exclude_none=True),
            }
        flow = FlowDefinition(
            name=flow_data.name,
            description=flow_data.description,
            version=flow_data.version,
            flow_data=flow_data.flow_data,
            entry_node_id=flow_data.entry_node_id,
            info=info_payload,
            is_published=False,
            is_active=flow_data.is_active if flow_data.is_active is not None else True,
            created_by=created_by,
            school_id=flow_data.school_id,
            visibility=flow_data.visibility,
        )

        db.add(flow)
        await db.flush()

        # Snapshot materialization is orchestrated by the service layer

        logger.info("Created flow", flow_id=flow.id, name=flow.name)

        return flow

    async def update_flow(
        self, db: AsyncSession, flow_id: UUID, update_data: FlowUpdate
    ) -> FlowDefinition:
        """Update existing flow."""
        query = select(FlowDefinition).where(FlowDefinition.id == flow_id)
        result = await db.execute(query)
        flow = result.scalar_one()

        # Update fields
        update_dict = update_data.model_dump(
            exclude_unset=True, exclude={"info", "contract"}
        )
        info_provided = "info" in update_data.model_fields_set
        contract_provided = "contract" in update_data.model_fields_set
        for field, value in update_dict.items():
            if hasattr(flow, field):
                setattr(flow, field, value)

        if info_provided:
            updated_info = update_data.info or {}
            if not contract_provided:
                existing_contract = flow.contract
                if existing_contract:
                    updated_info = {**updated_info, "contract": existing_contract}
            flow.info = updated_info

        if contract_provided:
            contract_payload = (
                update_data.contract.model_dump(exclude_none=True)
                if update_data.contract is not None
                else None
            )
            flow.contract = contract_payload

        await db.flush()

        logger.info("Updated flow", flow_id=flow_id)

        return flow

    async def clone_flow(
        self,
        db: AsyncSession,
        source_flow: FlowDefinition,
        new_name: str,
        created_by: Optional[UUID] = None,
        new_description: Optional[str] = None,
        version: Optional[str] = None,
        info_override: Optional[Dict[str, Any]] = None,
        clone_nodes: bool = True,
        clone_connections: bool = True,
    ) -> FlowDefinition:
        """Clone an existing flow with all its nodes and connections."""
        # Create new flow
        cloned_flow = FlowDefinition(
            name=new_name,
            description=new_description or source_flow.description,
            info=(info_override or (source_flow.info or {})),
            version=version or "1.0",
            flow_data=source_flow.flow_data or {},
            entry_node_id=source_flow.entry_node_id,
            is_active=True,
            is_published=False,
            created_by=created_by,
            school_id=source_flow.school_id,
            visibility=source_flow.visibility,
            trace_enabled=source_flow.trace_enabled,
            trace_sample_rate=source_flow.trace_sample_rate,
            retention_days=source_flow.retention_days,
        )

        db.add(cloned_flow)
        await db.flush()

        # Optionally clone nodes and connections
        await self._clone_nodes_and_connections(
            db,
            source_flow.id,
            cloned_flow.id,
            clone_nodes=clone_nodes,
            clone_connections=clone_connections,
        )

        logger.info(
            "Cloned flow",
            source_id=source_flow.id,
            cloned_id=cloned_flow.id,
            new_name=new_name,
        )

        return cloned_flow

    async def publish_flow(
        self,
        db: AsyncSession,
        flow_id: UUID,
        published_by_user_id: Optional[UUID],
        version: Optional[str] = None,
    ) -> FlowDefinition:
        """Publish a flow for use in conversations."""
        from datetime import datetime

        query = select(FlowDefinition).where(FlowDefinition.id == flow_id)
        result = await db.execute(query)
        flow = result.scalar_one()

        flow.is_published = True
        flow.published_at = datetime.utcnow()
        flow.published_by = published_by_user_id

        if version:
            flow.version = version
        else:
            # Auto-increment minor version if not explicitly provided
            try:
                parts = (flow.version or "1.0.0").split(".")
                major = int(parts[0]) if len(parts) > 0 else 1
                minor = int(parts[1]) + 1 if len(parts) > 1 else 1
                patch = int(parts[2]) if len(parts) > 2 else 0
                flow.version = f"{major}.{minor}.{patch}"
            except Exception:
                # Fallback if current version malformed
                flow.version = "1.1.0"

        await db.flush()

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

        await db.flush()

        logger.info("Unpublished flow", flow_id=flow_id)

        return flow

    async def soft_delete_flow(self, db: AsyncSession, flow_id: UUID) -> FlowDefinition:
        """Soft delete flow by setting is_active=False."""
        query = select(FlowDefinition).where(FlowDefinition.id == flow_id)
        result = await db.execute(query)
        flow = result.scalar_one()

        flow.is_active = False

        await db.flush()

        logger.info("Soft deleted flow", flow_id=flow_id)

        return flow

    async def get_nodes_by_flow(
        self, db: AsyncSession, flow_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[FlowNode]:
        """Get nodes for a specific flow with pagination."""
        query = (
            select(FlowNode)
            .where(FlowNode.flow_id == flow_id)
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        nodes = result.scalars().all()

        logger.debug("Found nodes for flow", flow_id=flow_id, count=len(nodes))

        return nodes

    async def count_nodes_by_flow(self, db: AsyncSession, flow_id: UUID) -> int:
        result = await db.execute(
            select(func.count(FlowNode.id)).where(FlowNode.flow_id == flow_id)
        )
        return int(result.scalar() or 0)

    async def get_node_by_db_id(
        self, db: AsyncSession, node_id: UUID
    ) -> Optional[FlowNode]:
        result = await db.execute(select(FlowNode).where(FlowNode.id == node_id))
        return result.scalar_one_or_none()

    async def create_node(
        self, db: AsyncSession, flow_id: UUID, node_data: NodeCreate
    ) -> FlowNode:
        """Create new node in flow."""
        node = FlowNode(
            flow_id=flow_id,
            node_id=node_data.node_id,
            node_type=node_data.node_type,
            template=node_data.template,
            content=node_data.content or {},
            position=node_data.position or {},
        )

        db.add(node)
        await db.flush()

        logger.info("Created node", node_id=node.id, flow_id=flow_id)

        return node

    async def update_node(
        self, db: AsyncSession, node_id: UUID, update_data: NodeUpdate
    ) -> FlowNode:
        """Update existing node."""
        query = select(FlowNode).where(FlowNode.id == node_id)
        result = await db.execute(query)
        node = result.scalar_one()

        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            if hasattr(node, field):
                setattr(node, field, value)

        await db.flush()

        logger.info("Updated node", node_id=node_id)

        return node

    async def delete_node_with_connections(
        self, db: AsyncSession, node_id: UUID
    ) -> bool:
        """Delete node and all its connections."""
        # Get the node
        node_query = select(FlowNode).where(FlowNode.id == node_id)
        node_result = await db.execute(node_query)
        node = node_result.scalar_one_or_none()

        if not node:
            return False

        # Delete connections that reference this node
        from sqlalchemy import or_

        connections_query = select(FlowConnection).where(
            or_(
                FlowConnection.source_node_id == node.node_id,
                FlowConnection.target_node_id == node.node_id,
            )
        )
        connections_result = await db.execute(connections_query)
        connections = connections_result.scalars().all()

        for connection in connections:
            await db.delete(connection)

        # Delete the node
        await db.delete(node)
        await db.flush()

        logger.info(
            "Deleted node with connections",
            node_id=node_id,
            connections_deleted=len(connections),
        )

        return True

    async def get_connections_by_flow(
        self, db: AsyncSession, flow_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[FlowConnection]:
        """Get connections for a specific flow with pagination."""
        query = (
            select(FlowConnection)
            .where(FlowConnection.flow_id == flow_id)
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        connections = result.scalars().all()

        logger.debug(
            "Found connections for flow", flow_id=flow_id, count=len(connections)
        )

        return connections

    async def count_connections_by_flow(self, db: AsyncSession, flow_id: UUID) -> int:
        result = await db.execute(
            select(func.count(FlowConnection.id)).where(
                FlowConnection.flow_id == flow_id
            )
        )
        return int(result.scalar() or 0)

    async def update_node_positions(
        self, db: AsyncSession, flow_id: UUID, positions: Dict[str, Dict[str, Any]]
    ) -> None:
        """Batch update node positions by node_id within a flow."""
        if not positions:
            return
        # Fetch all nodes for flow
        result = await db.execute(select(FlowNode).where(FlowNode.flow_id == flow_id))
        nodes = result.scalars().all()
        pos_map = positions
        for n in nodes:
            if n.node_id in pos_map:
                n.position = pos_map.get(n.node_id) or {"x": 0, "y": 0}
        await db.flush()

    async def create_connection(
        self, db: AsyncSession, flow_id: UUID, connection_data: ConnectionCreate
    ) -> FlowConnection:
        """Create new connection in flow."""
        connection = FlowConnection(
            flow_id=flow_id,
            source_node_id=connection_data.source_node_id,
            target_node_id=connection_data.target_node_id,
            connection_type=connection_data.connection_type,
            conditions=connection_data.conditions or {},
            info=connection_data.info or {},
        )

        db.add(connection)
        await db.flush()

        logger.info("Created connection", connection_id=connection.id, flow_id=flow_id)

        return connection

    async def delete_connection(self, db: AsyncSession, connection_id: UUID) -> bool:
        """Delete connection by ID."""
        query = select(FlowConnection).where(FlowConnection.id == connection_id)
        result = await db.execute(query)
        connection = result.scalar_one_or_none()

        if not connection:
            return False

        await db.delete(connection)
        await db.flush()

        logger.info("Deleted connection", connection_id=connection_id)

        return True

    async def get_connection_by_id(
        self, db: AsyncSession, connection_id: UUID
    ) -> Optional[FlowConnection]:
        result = await db.execute(
            select(FlowConnection).where(FlowConnection.id == connection_id)
        )
        return result.scalar_one_or_none()

    async def _clone_nodes_and_connections(
        self,
        db: AsyncSession,
        source_flow_id: UUID,
        target_flow_id: UUID,
        *,
        clone_nodes: bool = True,
        clone_connections: bool = True,
    ) -> None:
        """Helper method to clone nodes and connections from source to target flow."""
        # Get source nodes and connections
        nodes_query = select(FlowNode).where(FlowNode.flow_id == source_flow_id)
        nodes_result = await db.execute(nodes_query)
        source_nodes = nodes_result.scalars().all()

        connections_query = select(FlowConnection).where(
            FlowConnection.flow_id == source_flow_id
        )
        connections_result = await db.execute(connections_query)
        source_connections = connections_result.scalars().all()

        # Clone nodes
        if clone_nodes:
            for source_node in source_nodes:
                cloned_node = FlowNode(
                    flow_id=target_flow_id,
                    node_id=source_node.node_id,
                    node_type=source_node.node_type,
                    content=source_node.content or {},
                    position=source_node.position or {},
                    info=getattr(source_node, "info", {}) or {},
                )
                db.add(cloned_node)

        # Clone connections
        if clone_connections:
            for source_connection in source_connections:
                cloned_connection = FlowConnection(
                    flow_id=target_flow_id,
                    source_node_id=source_connection.source_node_id,
                    target_node_id=source_connection.target_node_id,
                    connection_type=source_connection.connection_type,
                    conditions=source_connection.conditions or {},
                    info=source_connection.info or {},
                )
                db.add(cloned_connection)

        await db.flush()

        logger.debug(
            "Cloned flow components",
            source_flow_id=source_flow_id,
            target_flow_id=target_flow_id,
            nodes_cloned=len(source_nodes),
            connections_cloned=len(source_connections),
        )

    # Snapshot regeneration moved to service layer
