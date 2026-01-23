"""Integration tests for session replay / execution trace feature."""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FlowDefinition
from app.models.cms import ConversationSession, FlowExecutionStep


@pytest.fixture
async def test_flow(async_session: AsyncSession) -> FlowDefinition:
    """Create a test flow for session replay testing."""
    flow = FlowDefinition(
        id=uuid4(),
        name=f"Session Replay Test Flow {uuid4().hex[:8]}",
        version="1.0.0",
        entry_node_id="start",
        flow_data={
            "nodes": {
                "start": {
                    "id": "start",
                    "type": "message",
                    "content": {"text": "Welcome to the test flow!"},
                    "connections": {"default": "question1"},
                },
                "question1": {
                    "id": "question1",
                    "type": "question",
                    "content": {
                        "text": "What is your favorite color?",
                        "options": [
                            {"label": "Red", "value": "red"},
                            {"label": "Blue", "value": "blue"},
                        ],
                    },
                    "connections": {"option_selected": "end"},
                },
                "end": {
                    "id": "end",
                    "type": "message",
                    "content": {"text": "Thank you for participating!"},
                    "connections": {},
                },
            }
        },
        retention_days=30,
        trace_enabled=True,
        trace_sample_rate=100,
    )
    async_session.add(flow)
    await async_session.commit()
    await async_session.refresh(flow)

    yield flow

    # Cleanup
    await async_session.delete(flow)
    await async_session.commit()


@pytest.fixture
async def test_sessions_with_traces(
    async_session: AsyncSession, test_flow: FlowDefinition
) -> list[ConversationSession]:
    """Create test sessions with execution trace data."""
    sessions = []

    # Session 1: Completed successfully with full trace
    session1 = ConversationSession(
        id=uuid4(),
        flow_id=test_flow.id,
        session_token=f"test-completed-{uuid4().hex}",
        current_node_id="end",
        state={"favorite_color": "blue"},
        info={"source": "test"},
        status="COMPLETED",
        trace_enabled=True,
        trace_level="standard",
    )
    async_session.add(session1)
    await async_session.flush()

    # Add execution steps for session 1
    steps1 = [
        FlowExecutionStep(
            session_id=session1.id,
            node_id="start",
            node_type="message",
            step_number=1,
            state_before={},
            state_after={},
            execution_details={"content": "Welcome to the test flow!"},
            connection_type="default",
            next_node_id="question1",
            duration_ms=45,
        ),
        FlowExecutionStep(
            session_id=session1.id,
            node_id="question1",
            node_type="question",
            step_number=2,
            state_before={},
            state_after={"favorite_color": "blue"},
            execution_details={
                "question": "What is your favorite color?",
                "selected": "Blue",
            },
            connection_type="option_selected",
            next_node_id="end",
            duration_ms=120,
        ),
        FlowExecutionStep(
            session_id=session1.id,
            node_id="end",
            node_type="message",
            step_number=3,
            state_before={"favorite_color": "blue"},
            state_after={"favorite_color": "blue"},
            execution_details={"content": "Thank you for participating!"},
            connection_type=None,
            next_node_id=None,
            duration_ms=25,
        ),
    ]
    for step in steps1:
        async_session.add(step)

    sessions.append(session1)

    # Session 2: Active session (in progress)
    session2 = ConversationSession(
        id=uuid4(),
        flow_id=test_flow.id,
        session_token=f"test-active-{uuid4().hex}",
        current_node_id="question1",
        state={},
        info={"source": "test"},
        status="ACTIVE",
        trace_enabled=True,
        trace_level="verbose",
    )
    async_session.add(session2)
    await async_session.flush()

    # Add execution steps for session 2
    step2 = FlowExecutionStep(
        session_id=session2.id,
        node_id="start",
        node_type="message",
        step_number=1,
        state_before={},
        state_after={},
        execution_details={"content": "Welcome to the test flow!"},
        connection_type="default",
        next_node_id="question1",
        duration_ms=38,
    )
    async_session.add(step2)

    sessions.append(session2)

    # Session 3: Session with error
    session3 = ConversationSession(
        id=uuid4(),
        flow_id=test_flow.id,
        session_token=f"test-error-{uuid4().hex}",
        current_node_id="question1",
        state={},
        info={"source": "test"},
        status="ACTIVE",
        trace_enabled=True,
        trace_level="standard",
    )
    async_session.add(session3)
    await async_session.flush()

    # Add execution step with error
    step3 = FlowExecutionStep(
        session_id=session3.id,
        node_id="start",
        node_type="message",
        step_number=1,
        state_before={},
        state_after={},
        execution_details={"content": "Welcome to the test flow!"},
        connection_type="default",
        next_node_id="question1",
        duration_ms=42,
        error_message="Test error occurred",
        error_details={"code": "TEST_ERROR", "message": "This is a test error"},
    )
    async_session.add(step3)

    sessions.append(session3)

    await async_session.commit()

    # Refresh all sessions
    for session in sessions:
        await async_session.refresh(session)

    yield sessions

    # Cleanup: Delete sessions (cascade will delete execution steps)
    for session in sessions:
        await async_session.delete(session)
    await async_session.commit()


class TestSessionListEndpoint:
    """Tests for the /flows/{flow_id}/sessions endpoint."""

    async def test_list_sessions_returns_all_sessions(
        self,
        async_client: AsyncClient,
        backend_service_account_headers: dict,
        test_flow: FlowDefinition,
        test_sessions_with_traces: list[ConversationSession],
    ):
        """Test that list sessions returns all sessions for a flow."""
        response = await async_client.get(
            f"/v1/cms/flows/{test_flow.id}/sessions",
            headers=backend_service_account_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert "total" in data
        assert data["total"] == 3
        assert len(data["items"]) == 3

        # Verify session data
        session_ids = {str(s.id) for s in test_sessions_with_traces}
        response_ids = {item["id"] for item in data["items"]}
        assert session_ids == response_ids

    async def test_list_sessions_filter_by_status(
        self,
        async_client: AsyncClient,
        backend_service_account_headers: dict,
        test_flow: FlowDefinition,
        test_sessions_with_traces: list[ConversationSession],
    ):
        """Test filtering sessions by status."""
        # Filter for completed sessions
        response = await async_client.get(
            f"/v1/cms/flows/{test_flow.id}/sessions",
            headers=backend_service_account_headers,
            params={"status": "COMPLETED"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert data["items"][0]["status"] == "completed"

    async def test_list_sessions_filter_by_errors(
        self,
        async_client: AsyncClient,
        backend_service_account_headers: dict,
        test_flow: FlowDefinition,
        test_sessions_with_traces: list[ConversationSession],
    ):
        """Test filtering sessions that have errors."""
        response = await async_client.get(
            f"/v1/cms/flows/{test_flow.id}/sessions",
            headers=backend_service_account_headers,
            params={"has_errors": True},
        )

        assert response.status_code == 200
        data = response.json()

        # Should return the session with the error step
        assert data["total"] == 1
        assert data["items"][0]["error_count"] > 0

    async def test_list_sessions_nonexistent_flow(
        self,
        async_client: AsyncClient,
        backend_service_account_headers: dict,
    ):
        """Test listing sessions for a nonexistent flow."""
        fake_flow_id = uuid4()
        response = await async_client.get(
            f"/v1/cms/flows/{fake_flow_id}/sessions",
            headers=backend_service_account_headers,
        )

        assert response.status_code == 404


class TestSessionTraceEndpoint:
    """Tests for the /sessions/{session_id}/trace endpoint."""

    async def test_get_session_trace(
        self,
        async_client: AsyncClient,
        backend_service_account_headers: dict,
        test_sessions_with_traces: list[ConversationSession],
    ):
        """Test retrieving execution trace for a session."""
        completed_session = test_sessions_with_traces[0]

        response = await async_client.get(
            f"/v1/cms/sessions/{completed_session.id}/trace",
            headers=backend_service_account_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify trace structure
        assert "session" in data
        assert "steps" in data
        assert "total_steps" in data
        assert "total_duration_ms" in data

        # Verify session info
        assert data["session"]["id"] == str(completed_session.id)
        assert data["session"]["status"] == "completed"

        # Verify steps
        assert data["total_steps"] == 3
        assert len(data["steps"]) == 3

        # Verify step order and content
        steps = sorted(data["steps"], key=lambda s: s["step_number"])
        assert steps[0]["node_id"] == "start"
        assert steps[0]["node_type"] == "message"
        assert steps[1]["node_id"] == "question1"
        assert steps[1]["node_type"] == "question"
        assert steps[2]["node_id"] == "end"
        assert steps[2]["node_type"] == "message"

    async def test_get_session_trace_with_error(
        self,
        async_client: AsyncClient,
        backend_service_account_headers: dict,
        test_sessions_with_traces: list[ConversationSession],
    ):
        """Test retrieving trace for session with errors."""
        error_session = test_sessions_with_traces[2]

        response = await async_client.get(
            f"/v1/cms/sessions/{error_session.id}/trace",
            headers=backend_service_account_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Find the step with error
        error_steps = [s for s in data["steps"] if s.get("error_message")]
        assert len(error_steps) == 1
        assert error_steps[0]["error_message"] == "Test error occurred"
        assert error_steps[0]["error_details"]["code"] == "TEST_ERROR"

    async def test_get_session_trace_nonexistent(
        self,
        async_client: AsyncClient,
        backend_service_account_headers: dict,
    ):
        """Test retrieving trace for nonexistent session."""
        fake_session_id = uuid4()
        response = await async_client.get(
            f"/v1/cms/sessions/{fake_session_id}/trace",
            headers=backend_service_account_headers,
        )

        assert response.status_code == 404

    async def test_get_session_trace_state_changes(
        self,
        async_client: AsyncClient,
        backend_service_account_headers: dict,
        test_sessions_with_traces: list[ConversationSession],
    ):
        """Test that trace includes state before/after for each step."""
        completed_session = test_sessions_with_traces[0]

        response = await async_client.get(
            f"/v1/cms/sessions/{completed_session.id}/trace",
            headers=backend_service_account_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Find the question step that changes state
        question_step = next(s for s in data["steps"] if s["node_id"] == "question1")

        assert question_step["state_before"] == {}
        assert question_step["state_after"] == {"favorite_color": "blue"}


class TestTracingConfig:
    """Tests for flow tracing configuration."""

    async def test_flow_has_tracing_fields(
        self,
        async_session: AsyncSession,
        test_flow: FlowDefinition,
    ):
        """Test that flow definition has tracing configuration fields."""
        result = await async_session.execute(
            select(FlowDefinition).where(FlowDefinition.id == test_flow.id)
        )
        flow = result.scalar_one()

        assert hasattr(flow, "retention_days")
        assert hasattr(flow, "trace_enabled")
        assert hasattr(flow, "trace_sample_rate")

        assert flow.retention_days == 30
        assert flow.trace_enabled is True
        assert flow.trace_sample_rate == 100

    async def test_session_has_trace_fields(
        self,
        async_session: AsyncSession,
        test_sessions_with_traces: list[ConversationSession],
    ):
        """Test that sessions have trace configuration fields."""
        for session in test_sessions_with_traces:
            result = await async_session.execute(
                select(ConversationSession).where(ConversationSession.id == session.id)
            )
            s = result.scalar_one()

            assert hasattr(s, "trace_enabled")
            assert hasattr(s, "trace_level")
            assert s.trace_enabled is True
            assert s.trace_level in ["standard", "verbose"]
