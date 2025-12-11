import pytest
from sqlalchemy import text

from app import crud
from app.models.cms import ConnectionType, NodeType
from app.repositories.flow_repository import FlowRepositoryImpl
from app.schemas.cms import ConnectionCreate, FlowCreate, NodeCreate
from app.services.flow_service import FlowService


@pytest.fixture(autouse=True)
async def cleanup_cms_data(async_session):
    tables = [
        "flow_connections",
        "flow_nodes",
        "flow_definitions",
        "conversation_sessions",
        "conversation_history",
        "conversation_analytics",
        "cms_content_variants",
        "cms_content",
    ]
    for t in tables:
        try:
            await async_session.execute(
                text(f"TRUNCATE TABLE {t} RESTART IDENTITY CASCADE")
            )
        except Exception:
            pass
    await async_session.commit()
    yield
    for t in tables:
        try:
            await async_session.execute(
                text(f"TRUNCATE TABLE {t} RESTART IDENTITY CASCADE")
            )
        except Exception:
            pass
    await async_session.commit()


@pytest.mark.asyncio
async def test_snapshot_regeneration_preserves_variables_and_updates_graph(
    async_session,
):
    # Create a flow with variables and a single node in flow_data
    flow_in = FlowCreate(
        name="Snapshot Flow",
        description="",
        version="1.0.0",
        flow_data={
            "variables": {"user": {"name": {"type": "string", "default": "Guest"}}},
            "nodes": [
                {
                    "id": "start",
                    "type": "message",
                    "content": {"messages": []},
                    "position": {"x": 0, "y": 0},
                }
            ],
            "connections": [],
        },
        entry_node_id="start",
        info={},
        is_published=False,
        is_active=True,
    )

    flow = await crud.flow.acreate(async_session, obj_in=flow_in)

    # Add a DB node and connection not yet reflected in the snapshot
    repo = FlowRepositoryImpl()
    await repo.create_node(
        async_session,
        flow_id=flow.id,
        node_data=NodeCreate(
            node_id="q1",
            node_type=NodeType.QUESTION,
            content={"question": {"text": "Favorite color?"}, "input_type": "text"},
            position={"x": 100, "y": 0},
            info={},
        ),
    )
    await repo.create_connection(
        async_session,
        flow_id=flow.id,
        connection_data=ConnectionCreate(
            source_node_id="start",
            target_node_id="q1",
            connection_type=ConnectionType.DEFAULT,
            conditions={},
            info={},
        ),
    )

    # Regenerate snapshot for this flow via service
    service = FlowService()
    stats = await service.regenerate_all_flow_data(async_session, [flow.id])
    assert stats["requested"] == 1 and stats["updated"] == 1 and not stats["errors"]

    # Reload flow and verify snapshot contains new graph pieces and preserved variables
    updated = await repo.get_flow_by_id(async_session, flow.id)
    assert updated is not None
    fd = updated.flow_data or {}
    assert "variables" in fd and fd["variables"]["user"]["name"]["default"] == "Guest"

    node_ids = {n.get("id") for n in fd.get("nodes", [])}
    assert {"start", "q1"}.issubset(node_ids)

    conn_pairs = {
        (c.get("source"), c.get("target"), c.get("type"))
        for c in fd.get("connections", [])
    }
    assert ("start", "q1", "DEFAULT") in conn_pairs
