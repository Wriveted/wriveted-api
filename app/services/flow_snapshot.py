from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cms import FlowConnection, FlowDefinition, FlowNode, NodeType
from app.services.flow_utils import enum_to_token, token_to_enum


async def build_snapshot_from_db(
    session: AsyncSession, flow_id: UUID, *, preserve: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Build a flow_data snapshot from canonical tables.

    If `preserve` is provided, non-graph keys from it will be retained.
    """
    query = (
        select(FlowDefinition)
        .options(
            selectinload(FlowDefinition.nodes), selectinload(FlowDefinition.connections)
        )
        .where(FlowDefinition.id == flow_id)
    )
    result = await session.execute(query)
    flow: FlowDefinition = result.scalar_one()

    existing = dict(preserve or flow.flow_data or {})

    # Build nodes
    nodes: List[Dict[str, Any]] = []
    for n in flow.nodes:
        nodes.append(
            {
                "id": n.node_id,
                "type": n.node_type.value.lower(),
                "content": n.content or {},
                "position": n.position or {"x": 0, "y": 0},
            }
        )

    # Build connections
    connections: List[Dict[str, Any]] = []
    for c in flow.connections:
        connections.append(
            {
                "source": c.source_node_id,
                "target": c.target_node_id,
                "type": enum_to_token(c.connection_type),
                "conditions": c.conditions or {},
                "info": c.info or {},
            }
        )

    # Preserve non-graph keys
    for k in ("nodes", "connections"):
        existing.pop(k, None)
    return {**existing, "nodes": nodes, "connections": connections}


async def materialize_snapshot(
    session: AsyncSession, flow_id: UUID, snapshot: Dict[str, Any]
) -> None:
    """Idempotently apply snapshot nodes/connections to canonical tables.

    Upserts nodes and connections present in the snapshot.
    """
    nodes = snapshot.get("nodes", []) or []
    connections = snapshot.get("connections", []) or []

    # Upsert nodes
    for node in nodes:
        node_id = node.get("id", "")
        if not node_id:
            continue
        # Fetch existing
        res = await session.execute(
            select(FlowNode).where(
                FlowNode.flow_id == flow_id, FlowNode.node_id == node_id
            )
        )
        existing: Optional[FlowNode] = res.scalar_one_or_none()

        # Map type
        type_str = (node.get("type") or "message").upper()
        node_type = {
            "MESSAGE": NodeType.MESSAGE,
            "QUESTION": NodeType.QUESTION,
            "CONDITION": NodeType.CONDITION,
            "ACTION": NodeType.ACTION,
            "WEBHOOK": NodeType.WEBHOOK,
            "COMPOSITE": NodeType.COMPOSITE,
        }.get(type_str, NodeType.MESSAGE)

        if existing is None:
            obj = FlowNode(
                flow_id=flow_id,
                node_id=node_id,
                node_type=node_type,
                content=node.get("content", {}) or {},
                position=node.get("position", {"x": 0, "y": 0}) or {},
                info=node.get("info", {}) or {},
            )
            session.add(obj)
        else:
            existing.node_type = node_type
            existing.content = node.get("content", {}) or {}
            existing.position = node.get("position", {"x": 0, "y": 0}) or {}
            existing.info = node.get("info", {}) or {}

    await session.flush()

    # Upsert connections
    for conn in connections:
        source = conn.get("source", "")
        target = conn.get("target", "")
        ctype = token_to_enum(conn.get("type"))
        if not source or not target:
            continue

        res = await session.execute(
            select(FlowConnection).where(
                FlowConnection.flow_id == flow_id,
                FlowConnection.source_node_id == source,
                FlowConnection.target_node_id == target,
                FlowConnection.connection_type == ctype,
            )
        )
        existing: Optional[FlowConnection] = res.scalar_one_or_none()
        if existing is None:
            obj = FlowConnection(
                flow_id=flow_id,
                source_node_id=source,
                target_node_id=target,
                connection_type=ctype,
                conditions=conn.get("conditions", {}) or {},
                info=conn.get("info", {}) or {},
            )
            session.add(obj)
        else:
            existing.conditions = conn.get("conditions", {}) or {}
            existing.info = conn.get("info", {}) or {}

    await session.flush()
