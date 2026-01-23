"""
Integration tests to verify EventOutbox entries are created for flow operations.

Covers:
- flow_created on POST /v1/cms/flows
- flow_updated on PUT /v1/cms/flows/{id}
- flow_published on PUT /v1/cms/flows/{id} with publish=true
"""

import pytest
from sqlalchemy import text
from starlette import status


@pytest.fixture(autouse=True)
async def cleanup_event_outbox(async_session):
    """Ensure event_outbox is clean before and after each test."""
    try:
        await async_session.execute(
            text("TRUNCATE TABLE event_outbox RESTART IDENTITY CASCADE")
        )
        await async_session.commit()
    except Exception:
        pass
    yield
    try:
        await async_session.execute(
            text("TRUNCATE TABLE event_outbox RESTART IDENTITY CASCADE")
        )
        await async_session.commit()
    except Exception:
        pass


async def _create_minimal_flow(async_client, headers):
    payload = {
        "name": "Outbox Test Flow",
        "description": "",
        "version": "1.0.0",
        "flow_data": {
            "nodes": [
                {
                    "id": "start",
                    "type": "message",
                    "content": {"messages": [{"type": "text", "content": "hi"}]},
                    "position": {"x": 0, "y": 0},
                }
            ],
            "connections": [],
        },
        "entry_node_id": "start",
        "info": {},
    }
    resp = await async_client.post("/v1/cms/flows", json=payload, headers=headers)
    assert resp.status_code == status.HTTP_201_CREATED
    return resp.json()


class TestFlowOutboxEvents:
    async def test_outbox_on_flow_create(
        self, async_client, async_session, backend_service_account_headers
    ):
        await _create_minimal_flow(async_client, backend_service_account_headers)
        result = await async_session.execute(
            text("SELECT COUNT(*) FROM event_outbox WHERE event_type = 'flow_created'")
        )
        count = int(result.scalar() or 0)
        assert count >= 1, "Expected flow_created event in outbox"

    async def test_outbox_on_flow_update(
        self, async_client, async_session, backend_service_account_headers
    ):
        flow = await _create_minimal_flow(async_client, backend_service_account_headers)
        update = {"description": "updated"}
        resp = await async_client.put(
            f"/v1/cms/flows/{flow['id']}",
            json=update,
            headers=backend_service_account_headers,
        )
        assert resp.status_code == status.HTTP_200_OK
        result = await async_session.execute(
            text("SELECT COUNT(*) FROM event_outbox WHERE event_type = 'flow_updated'")
        )
        count = int(result.scalar() or 0)
        assert count >= 1, "Expected flow_updated event in outbox"

    async def test_outbox_on_flow_publish(
        self, async_client, async_session, backend_service_account_headers
    ):
        flow = await _create_minimal_flow(async_client, backend_service_account_headers)
        resp = await async_client.put(
            f"/v1/cms/flows/{flow['id']}",
            json={"publish": True},
            headers=backend_service_account_headers,
        )
        assert resp.status_code == status.HTTP_200_OK
        result = await async_session.execute(
            text(
                "SELECT COUNT(*) FROM event_outbox WHERE event_type = 'flow_published'"
            )
        )
        count = int(result.scalar() or 0)
        assert count >= 1, "Expected flow_published event in outbox"
