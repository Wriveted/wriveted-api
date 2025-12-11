"""
Integration tests for execution trace and session replay functionality.

Tests cover:
- ExecutionTraceService for recording and retrieving traces
- TraceAuditService for audit logging
- API endpoints for session replay
- PII masking in trace data
"""

import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy import text
from starlette import status


# Test isolation fixture for execution trace data
@pytest.fixture(autouse=True)
async def cleanup_trace_data(async_session):
    """Clean up trace and CMS data before and after each test."""
    trace_tables = [
        "flow_execution_steps",
        "trace_access_audit",
        "conversation_sessions",
        "conversation_history",
        "conversation_analytics",
        "flow_definitions",
        "flow_nodes",
        "flow_connections",
    ]

    # Clean up before test runs
    for table in trace_tables:
        try:
            await async_session.execute(
                text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
            )
        except Exception:
            # Table might not exist yet (migration not run)
            pass
    await async_session.commit()

    yield

    # Clean up after test runs
    for table in trace_tables:
        try:
            await async_session.execute(
                text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
            )
        except Exception:
            pass
    await async_session.commit()


@pytest.fixture
async def trace_test_flow(async_client, backend_service_account_headers):
    """Create a flow for trace testing with tracing enabled."""
    flow_data = {
        "name": f"Trace Test Flow {uuid.uuid4().hex[:8]}",
        "description": "Flow for testing execution traces",
        "version": "1.0.0",
        "flow_data": {
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "content": {},
                    "position": {"x": 100, "y": 100},
                },
                {
                    "id": "greeting",
                    "type": "message",
                    "content": {"messages": [{"type": "text", "content": "Hello!"}]},
                    "position": {"x": 200, "y": 100},
                },
                {
                    "id": "question",
                    "type": "question",
                    "content": {"question": "What is your name?", "input_type": "text"},
                    "position": {"x": 300, "y": 100},
                },
            ],
            "connections": [
                {"source": "start", "target": "greeting", "type": "default"},
                {"source": "greeting", "target": "question", "type": "default"},
            ],
        },
        "entry_node_id": "start",
    }

    response = await async_client.post(
        "/v1/cms/flows", json=flow_data, headers=backend_service_account_headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    flow = response.json()

    # Publish the flow
    publish_response = await async_client.post(
        f"/v1/cms/flows/{flow['id']}/publish", headers=backend_service_account_headers
    )
    assert publish_response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    return flow


class TestExecutionTraceService:
    """Test the ExecutionTraceService functionality."""

    @pytest.fixture(autouse=True)
    def setup_test(self, reset_global_state_sync):
        """Ensure global state is reset before each test."""
        pass

    async def test_record_step_basic(self, async_session, trace_test_flow):
        """Test recording a basic execution step."""
        from app.models.cms import ConversationSession, SessionStatus
        from app.services.execution_trace import ExecutionTraceService

        service = ExecutionTraceService()

        # Create a test session
        session = ConversationSession(
            session_token=f"test-{uuid.uuid4().hex[:8]}",
            flow_id=uuid.UUID(trace_test_flow["id"]),
            status=SessionStatus.ACTIVE,
            current_node_id="start",
            session_data={"trace_enabled": True},
        )
        async_session.add(session)
        await async_session.flush()

        # Record a step
        step = await service.record_step(
            db=async_session,
            session_id=session.id,
            node_id="start",
            node_type="start",
            step_number=1,
            state_before={},
            state_after={"initialized": True},
            execution_details={"type": "start", "entry_point": True},
            connection_type="default",
            next_node_id="greeting",
            started_at=datetime.utcnow(),
            duration_ms=10,
        )

        assert step is not None
        assert step.node_id == "start"
        assert step.node_type == "start"
        assert step.step_number == 1
        assert step.duration_ms == 10

    async def test_record_step_with_pii_masking(self, async_session, trace_test_flow):
        """Test that PII is properly masked when recording steps."""
        from app.models.cms import ConversationSession, SessionStatus
        from app.services.execution_trace import ExecutionTraceService

        service = ExecutionTraceService()

        # Create a test session
        session = ConversationSession(
            session_token=f"test-{uuid.uuid4().hex[:8]}",
            flow_id=uuid.UUID(trace_test_flow["id"]),
            status=SessionStatus.ACTIVE,
            current_node_id="question",
            session_data={},
        )
        async_session.add(session)
        await async_session.flush()

        # Record step with PII in state
        state_with_pii = {
            "user_email": "john@example.com",
            "phone_number": "+1-555-123-4567",
            "message": "Contact me at jane@test.com",
            "count": 42,  # Non-sensitive
        }

        step = await service.record_step(
            db=async_session,
            session_id=session.id,
            node_id="question",
            node_type="question",
            step_number=1,
            state_before={},
            state_after=state_with_pii,
            execution_details={"type": "question"},
        )

        # Verify PII was masked
        assert "john@example.com" not in str(step.state_after)
        assert "+1-555-123-4567" not in str(step.state_after)
        assert "[MASKED:" in step.state_after.get("user_email", "")
        assert "[MASKED:" in step.state_after.get("phone_number", "")
        assert "[EMAIL]" in step.state_after.get("message", "")
        assert step.state_after.get("count") == 42  # Non-sensitive preserved

    async def test_get_session_trace(self, async_session, trace_test_flow):
        """Test retrieving a full session trace."""
        from app.models.cms import ConversationSession, SessionStatus
        from app.services.execution_trace import ExecutionTraceService

        service = ExecutionTraceService()

        # Create a test session with multiple steps
        session = ConversationSession(
            session_token=f"test-{uuid.uuid4().hex[:8]}",
            flow_id=uuid.UUID(trace_test_flow["id"]),
            status=SessionStatus.COMPLETED,
            current_node_id="question",
            session_data={},
            started_at=datetime.utcnow() - timedelta(minutes=5),
            ended_at=datetime.utcnow(),
        )
        async_session.add(session)
        await async_session.flush()

        # Record multiple steps
        for i, (node_id, node_type) in enumerate(
            [
                ("start", "start"),
                ("greeting", "message"),
                ("question", "question"),
            ],
            start=1,
        ):
            await service.record_step(
                db=async_session,
                session_id=session.id,
                node_id=node_id,
                node_type=node_type,
                step_number=i,
                state_before={},
                state_after={"step": i},
                execution_details={"type": node_type},
                duration_ms=10 * i,
            )

        await async_session.commit()

        # Get the trace
        trace = await service.get_session_trace(async_session, session.id)

        assert trace["total_steps"] == 3
        assert trace["total_duration_ms"] == 60  # 10 + 20 + 30
        assert len(trace["steps"]) == 3
        assert trace["steps"][0]["node_id"] == "start"
        assert trace["steps"][1]["node_id"] == "greeting"
        assert trace["steps"][2]["node_id"] == "question"

    async def test_list_flow_sessions(self, async_session, trace_test_flow):
        """Test listing sessions for a flow with filtering."""
        from app.models.cms import ConversationSession, SessionStatus
        from app.services.execution_trace import ExecutionTraceService

        service = ExecutionTraceService()
        flow_id = uuid.UUID(trace_test_flow["id"])

        # Create multiple sessions
        for i in range(5):
            session = ConversationSession(
                session_token=f"test-{i}-{uuid.uuid4().hex[:8]}",
                flow_id=flow_id,
                status=SessionStatus.COMPLETED if i < 3 else SessionStatus.ACTIVE,
                current_node_id="question",
                session_data={},
                started_at=datetime.utcnow() - timedelta(hours=i),
            )
            async_session.add(session)

        await async_session.flush()
        await async_session.commit()

        # List all sessions
        result = await service.list_flow_sessions(async_session, flow_id)

        assert result["total"] == 5
        assert len(result["items"]) == 5

        # List with status filter
        result_completed = await service.list_flow_sessions(
            async_session, flow_id, status="completed"
        )
        assert result_completed["total"] >= 3

    async def test_should_trace_session_sampling(self, async_session, trace_test_flow):
        """Test that session tracing respects sample rate."""
        from sqlalchemy import select

        from app.models.cms import FlowDefinition
        from app.services.execution_trace import ExecutionTraceService

        service = ExecutionTraceService()
        flow_id = uuid.UUID(trace_test_flow["id"])

        # Get and update flow to enable tracing with sample rate
        result = await async_session.execute(
            select(FlowDefinition).where(FlowDefinition.id == flow_id)
        )
        flow = result.scalar_one()
        flow.trace_enabled = True
        flow.trace_sample_rate = 50  # 50% sampling
        await async_session.flush()
        await async_session.commit()

        # Test multiple sessions - should get roughly 50% traced
        traced_count = 0
        total_tests = 100

        for i in range(total_tests):
            session_token = f"test-{i}-{uuid.uuid4().hex[:8]}"
            should_trace = await service.should_trace_session(
                async_session, flow_id, session_token
            )
            if should_trace:
                traced_count += 1

        # With 50% sample rate, expect roughly half
        # Allow for statistical variance (30-70% range)
        assert 30 <= traced_count <= 70, f"Expected ~50%, got {traced_count}%"

    async def test_build_execution_details_condition(self, async_session):
        """Test building execution details for condition nodes."""
        from app.services.execution_trace import ExecutionTraceService

        service = ExecutionTraceService()

        result = {
            "condition_results": {"0": True, "1": False},
            "matched_index": 0,
            "connection_type": "condition_0",
        }
        content = {
            "conditions": [
                {"if": {"var": "score", "op": ">", "value": 50}},
                {"if": {"var": "score", "op": ">", "value": 30}},
            ]
        }

        details = service.build_execution_details("condition", result, content)

        assert details["type"] == "condition"
        assert len(details["conditions_evaluated"]) == 2
        assert details["matched_condition_index"] == 0
        assert details["connection_taken"] == "condition_0"

    async def test_build_execution_details_script(self, async_session):
        """Test building execution details for script nodes."""
        from app.services.execution_trace import ExecutionTraceService

        service = ExecutionTraceService()

        result = {
            "inputs": {"x": 10},
            "outputs": {"y": 20},
            "console_logs": ["Processing..."],
            "execution_time_ms": 15,
        }
        content = {"language": "javascript", "code": "return { y: x * 2 };"}

        details = service.build_execution_details("script", result, content)

        assert details["type"] == "script"
        assert details["language"] == "javascript"
        assert details["inputs"] == {"x": 10}
        assert details["outputs"] == {"y": 20}
        assert details["execution_time_ms"] == 15


class TestTraceAuditService:
    """Test the TraceAuditService functionality."""

    @pytest.fixture(autouse=True)
    def setup_test(self, reset_global_state_sync):
        """Ensure global state is reset before each test."""
        pass

    async def test_log_access(self, async_session, trace_test_flow, wriveted_admin):
        """Test logging trace access."""
        from sqlalchemy import select

        from app.models.cms import ConversationSession, SessionStatus, TraceAccessAudit
        from app.services.execution_trace import TraceAuditService

        service = TraceAuditService()

        # Create a test session
        session = ConversationSession(
            session_token=f"test-{uuid.uuid4().hex[:8]}",
            flow_id=uuid.UUID(trace_test_flow["id"]),
            status=SessionStatus.COMPLETED,
            current_node_id="question",
            session_data={},
        )
        async_session.add(session)
        await async_session.flush()

        # Log access
        await service.log_access(
            db=async_session,
            session_id=session.id,
            accessed_by=wriveted_admin.id,
            access_type="view_trace",
            ip_address="192.168.1.1",
            user_agent="Test Client",
        )

        await async_session.commit()

        # Verify audit log was created
        result = await async_session.execute(
            select(TraceAccessAudit).where(TraceAccessAudit.session_id == session.id)
        )
        audit = result.scalar_one()

        assert audit.access_type == "view_trace"
        assert audit.ip_address == "192.168.1.1"
        assert audit.accessed_by == wriveted_admin.id


class TestSessionReplayAPI:
    """Test API endpoints for session replay."""

    @pytest.fixture(autouse=True)
    def setup_test(self, reset_global_state_sync):
        """Ensure global state is reset before each test."""
        pass

    async def test_list_flow_sessions_endpoint(
        self, async_client, backend_service_account_headers, trace_test_flow
    ):
        """Test GET /flows/{flow_id}/sessions endpoint."""
        flow_id = trace_test_flow["id"]

        response = await async_client.get(
            f"/v1/cms/flows/{flow_id}/sessions", headers=backend_service_account_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    async def test_get_session_trace_endpoint(
        self,
        async_client,
        async_session,
        backend_service_account_headers,
        trace_test_flow,
    ):
        """Test GET /sessions/{session_id}/trace endpoint."""
        from app.models.cms import ConversationSession, SessionStatus
        from app.services.execution_trace import ExecutionTraceService

        # Create a session with trace data
        session = ConversationSession(
            session_token=f"test-{uuid.uuid4().hex[:8]}",
            flow_id=uuid.UUID(trace_test_flow["id"]),
            status=SessionStatus.COMPLETED,
            current_node_id="question",
            session_data={},
        )
        async_session.add(session)
        await async_session.flush()

        # Add a trace step
        service = ExecutionTraceService()
        await service.record_step(
            db=async_session,
            session_id=session.id,
            node_id="start",
            node_type="start",
            step_number=1,
            state_before={},
            state_after={},
            execution_details={"type": "start"},
        )
        await async_session.commit()

        # Get the trace via API
        response = await async_client.get(
            f"/v1/cms/sessions/{session.id}/trace",
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_steps"] == 1
        assert len(data["steps"]) == 1

    async def test_configure_tracing_endpoint(
        self, async_client, backend_service_account_headers, trace_test_flow
    ):
        """Test POST /flows/{flow_id}/tracing endpoint."""
        flow_id = trace_test_flow["id"]

        response = await async_client.post(
            f"/v1/cms/flows/{flow_id}/tracing",
            json={
                "enabled": True,
                "level": "verbose",
                "sample_rate": 0.5,
            },
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["enabled"] is True
        assert data["level"] == "verbose"

    async def test_get_tracing_config_endpoint(
        self, async_client, backend_service_account_headers, trace_test_flow
    ):
        """Test GET /flows/{flow_id}/tracing endpoint."""
        flow_id = trace_test_flow["id"]

        response = await async_client.get(
            f"/v1/cms/flows/{flow_id}/tracing", headers=backend_service_account_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "enabled" in data
        assert "flow_id" in data

    async def test_get_trace_stats_endpoint(
        self, async_client, backend_service_account_headers, trace_test_flow
    ):
        """Test GET /flows/{flow_id}/trace-stats endpoint."""
        flow_id = trace_test_flow["id"]

        response = await async_client.get(
            f"/v1/cms/flows/{flow_id}/trace-stats",
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "traced_sessions" in data
        assert "total_steps" in data

    async def test_get_storage_stats_endpoint(
        self, async_client, backend_service_account_headers
    ):
        """Test GET /trace-storage endpoint."""
        response = await async_client.get(
            "/v1/cms/trace-storage", headers=backend_service_account_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_traces" in data
        assert "table_size" in data

    async def test_trace_endpoints_require_auth(self, async_client, trace_test_flow):
        """Test that trace endpoints require authentication."""
        flow_id = trace_test_flow["id"]

        # All these should require auth
        endpoints = [
            ("GET", f"/v1/cms/flows/{flow_id}/sessions"),
            ("GET", f"/v1/cms/flows/{flow_id}/tracing"),
            ("POST", f"/v1/cms/flows/{flow_id}/tracing"),
            ("GET", f"/v1/cms/flows/{flow_id}/trace-stats"),
            ("GET", "/v1/cms/trace-storage"),
        ]

        for method, endpoint in endpoints:
            if method == "GET":
                response = await async_client.get(endpoint)
            else:
                response = await async_client.post(endpoint, json={})

            # Should require authentication
            assert response.status_code in [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ], f"Expected auth required for {method} {endpoint}"


class TestTraceCleanupService:
    """Test the TraceCleanupService functionality."""

    @pytest.fixture(autouse=True)
    def setup_test(self, reset_global_state_sync):
        """Ensure global state is reset before each test."""
        pass

    async def test_get_storage_stats(self, async_session):
        """Test getting storage statistics."""
        from app.services.trace_cleanup import TraceCleanupService

        service = TraceCleanupService()
        stats = await service.get_storage_stats(async_session)

        assert "total_traces" in stats
        assert "table_size" in stats
        assert isinstance(stats["total_traces"], int)

    async def test_get_flow_trace_stats(self, async_session, trace_test_flow):
        """Test getting trace statistics for a specific flow."""
        from app.services.trace_cleanup import TraceCleanupService

        service = TraceCleanupService()
        flow_id = trace_test_flow["id"]

        stats = await service.get_flow_trace_stats(async_session, flow_id)

        assert "traced_sessions" in stats
        assert "total_steps" in stats
        assert "avg_step_duration_ms" in stats
        assert "error_steps" in stats
