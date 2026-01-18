from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cms import FlowConnection, FlowDefinition, FlowNode, NodeType
from app.services.flow_utils import enum_to_token, token_to_enum


def _safe_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _normalize_position(position: Any) -> Dict[str, Any]:
    if not isinstance(position, dict):
        return {"x": 0, "y": 0}
    return {"x": position.get("x", 0), "y": position.get("y", 0)}


def _extract_node_id(node: Dict[str, Any]) -> str:
    for key in ("id", "node_id", "node_key"):
        value = node.get(key)
        if value:
            return str(value)
    data = _safe_dict(node.get("data"))
    value = data.get("id")
    return str(value) if value else ""


def _extract_node_type(node: Dict[str, Any]) -> NodeType:
    raw_type = node.get("node_type") or node.get("type")
    if not raw_type or str(raw_type).lower() == "custom":
        data = _safe_dict(node.get("data"))
        raw_type = data.get("nodeType") or data.get("node_type")

    if isinstance(raw_type, NodeType):
        return raw_type

    type_key = str(raw_type or "message").upper()
    type_map = {
        "START": NodeType.START,
        "MESSAGE": NodeType.MESSAGE,
        "QUESTION": NodeType.QUESTION,
        "CONDITION": NodeType.CONDITION,
        "ACTION": NodeType.ACTION,
        "WEBHOOK": NodeType.WEBHOOK,
        "COMPOSITE": NodeType.COMPOSITE,
        "SCRIPT": NodeType.SCRIPT,
    }
    return type_map.get(type_key, NodeType.MESSAGE)


def _extract_node_content(node: Dict[str, Any]) -> Dict[str, Any]:
    content = node.get("content")
    if content is None:
        content = _safe_dict(node.get("data")).get("content")
    return content or {}


def _extract_node_template(node: Dict[str, Any]) -> Optional[str]:
    template = node.get("template")
    if template is None:
        template = _safe_dict(node.get("data")).get("template")
    return template


def _extract_node_info(node: Dict[str, Any]) -> Dict[str, Any]:
    info = node.get("info")
    if info is None:
        data = _safe_dict(node.get("data"))
        info = data.get("info") or data.get("meta_data")
    return info or {}


def _extract_node_position(node: Dict[str, Any]) -> Dict[str, Any]:
    position = (
        node.get("position")
        or node.get("position_absolute")
        or _safe_dict(node.get("data")).get("position")
    )
    return _normalize_position(position)


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
                "template": n.template,
                "position": n.position or {"x": 0, "y": 0},
                "info": n.info or {},
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
    connections = snapshot.get("connections", []) or snapshot.get("edges", []) or []

    # Upsert nodes
    for node in nodes:
        node_id = _extract_node_id(node)
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
        node_type = _extract_node_type(node)
        content = _extract_node_content(node)
        template = _extract_node_template(node)
        info = _extract_node_info(node)
        position = _extract_node_position(node)

        if existing is None:
            obj = FlowNode(
                flow_id=flow_id,
                node_id=node_id,
                node_type=node_type,
                template=template,
                content=content,
                position=position,
                info=info,
            )
            session.add(obj)
        else:
            existing.node_type = node_type
            existing.template = template
            existing.content = content
            existing.position = position
            existing.info = info

    await session.flush()

    # Upsert connections
    for conn in connections:
        data = _safe_dict(conn.get("data"))
        source = conn.get("source") or conn.get("source_node_id") or ""
        target = conn.get("target") or conn.get("target_node_id") or ""
        raw_type = (
            conn.get("connection_type")
            or data.get("connection_type")
            or conn.get("type")
            or data.get("type")
        )
        ctype = token_to_enum(raw_type)
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
                conditions=conn.get("conditions") or data.get("conditions") or {},
                info=conn.get("info") or data.get("info") or {},
            )
            session.add(obj)
        else:
            existing.conditions = conn.get("conditions") or data.get("conditions") or {}
            existing.info = conn.get("info") or data.get("info") or {}

    await session.flush()
