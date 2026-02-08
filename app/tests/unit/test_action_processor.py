"""
Unit tests for action_processor helpers and API call handling.

Tests _strip_unresolved_templates (pure function) and the internal handler
fallback_response mechanism without database dependencies.
"""

import uuid
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.models.cms import FlowNode, NodeType, SessionStatus
from app.services.action_processor import (
    ActionNodeProcessor,
    _strip_unresolved_templates,
)

# ---------------------------------------------------------------------------
# Fixtures (shared with test_aggregate_action.py pattern)
# ---------------------------------------------------------------------------


class MockSession:
    def __init__(self, state=None):
        self.id = uuid.uuid4()
        self.user_id = uuid.uuid4()
        self.flow_id = uuid.uuid4()
        self.session_token = "test_token"
        self.current_node_id = "test_node"
        self.state = state or {}
        self.revision = 1
        self.status = SessionStatus.ACTIVE


@pytest.fixture
def mock_runtime():
    runtime = Mock()
    runtime.substitute_variables = Mock(side_effect=lambda v, s: v)
    runtime.substitute_object = Mock(side_effect=lambda v, s: v)
    runtime.process_node = AsyncMock()
    return runtime


@pytest.fixture
def action_processor(mock_runtime):
    return ActionNodeProcessor(mock_runtime)


@pytest.fixture
def mock_db():
    return AsyncMock()


def _make_action_node(flow_id, content):
    node = Mock(spec=FlowNode)
    node.id = uuid.uuid4()
    node.flow_id = flow_id
    node.node_id = f"action_{uuid.uuid4().hex[:8]}"
    node.node_type = NodeType.ACTION
    node.content = content
    node.template = None
    node.position = {"x": 0, "y": 0}
    return node


def _setup_chat_repo(mock_repo):
    mock_repo.update_session_state = AsyncMock()
    mock_repo.add_interaction_history = AsyncMock()
    mock_repo.get_flow_node = AsyncMock(return_value=None)
    mock_repo.get_node_connections = AsyncMock(return_value=[])


# ---------------------------------------------------------------------------
# _strip_unresolved_templates
# ---------------------------------------------------------------------------


class TestStripUnresolvedTemplates:
    """Test the _strip_unresolved_templates pure function."""

    def test_resolves_simple_template_to_none(self):
        assert _strip_unresolved_templates("{{user.name}}") is None

    def test_resolves_template_with_surrounding_text(self):
        assert _strip_unresolved_templates("Hello {{user.name}}!") is None

    def test_preserves_plain_string(self):
        assert _strip_unresolved_templates("hello world") == "hello world"

    def test_preserves_empty_string(self):
        assert _strip_unresolved_templates("") == ""

    def test_preserves_non_string_types(self):
        assert _strip_unresolved_templates(42) == 42
        assert _strip_unresolved_templates(3.14) == 3.14
        assert _strip_unresolved_templates(True) is True
        assert _strip_unresolved_templates(None) is None

    def test_strips_in_nested_dict(self):
        result = _strip_unresolved_templates(
            {"name": "Brian", "school_id": "{{context.school_wriveted_id}}"}
        )
        assert result == {"name": "Brian", "school_id": None}

    def test_strips_in_nested_list(self):
        result = _strip_unresolved_templates(["ok", "{{temp.x}}", 123])
        assert result == ["ok", None, 123]

    def test_strips_in_deeply_nested_structure(self):
        result = _strip_unresolved_templates(
            {"outer": {"inner": [{"val": "{{user.id}}"}]}}
        )
        assert result == {"outer": {"inner": [{"val": None}]}}

    def test_preserves_dict_with_no_templates(self):
        data = {"a": 1, "b": "hello", "c": [1, 2]}
        assert _strip_unresolved_templates(data) == data

    def test_stray_braces_not_matching_template_pattern(self):
        """Strings with {{ or }} alone (not forming a template) are preserved."""
        assert _strip_unresolved_templates("has }} only") == "has }} only"
        assert _strip_unresolved_templates("has {{ only") == "has {{ only"

    def test_empty_template_braces(self):
        """{{}} is technically a template pattern and should be stripped."""
        assert _strip_unresolved_templates("{{}}") is None

    def test_multiple_templates_in_one_string(self):
        assert _strip_unresolved_templates("{{a}} and {{b}}") is None


# ---------------------------------------------------------------------------
# Internal handler fallback_response
# ---------------------------------------------------------------------------


class TestInternalHandlerFallback:
    """Test the fallback_response mechanism in _handle_api_call."""

    @pytest.mark.asyncio
    @patch("app.services.chat_runtime.chat_repo")
    @patch("app.services.action_processor.chat_repo")
    @patch("app.services.internal_api_handlers.INTERNAL_HANDLERS", new_callable=dict)
    async def test_fallback_used_when_handler_raises(
        self,
        mock_handlers,
        mock_action_chat_repo,
        mock_runtime_chat_repo,
        action_processor,
        mock_db,
    ):
        """When an internal handler raises and fallback_response is defined, use it."""
        _setup_chat_repo(mock_action_chat_repo)
        _setup_chat_repo(mock_runtime_chat_repo)

        mock_handlers["/v1/recommend"] = AsyncMock(
            side_effect=ValueError("bad UUID")
        )

        session = MockSession()
        node = _make_action_node(
            session.flow_id,
            {
                "actions": [
                    {
                        "type": "api_call",
                        "config": {
                            "endpoint": "/v1/recommend",
                            "auth_type": "internal",
                            "body": {},
                            "fallback_response": {"books": [], "count": 0},
                            "response_mapping": {
                                "count": "temp.book_count",
                            },
                        },
                    }
                ]
            },
        )

        result = await action_processor.process(
            mock_db, node, session, {"db": mock_db}
        )

        assert result["success"] is True
        assert result["variables"]["temp"]["book_count"] == 0

    @pytest.mark.asyncio
    @patch("app.services.chat_runtime.chat_repo")
    @patch("app.services.action_processor.chat_repo")
    @patch("app.services.internal_api_handlers.INTERNAL_HANDLERS", new_callable=dict)
    async def test_exception_propagates_without_fallback(
        self,
        mock_handlers,
        mock_action_chat_repo,
        mock_runtime_chat_repo,
        action_processor,
        mock_db,
    ):
        """When an internal handler raises and no fallback_response, exception propagates."""
        _setup_chat_repo(mock_action_chat_repo)
        _setup_chat_repo(mock_runtime_chat_repo)

        mock_handlers["/v1/recommend"] = AsyncMock(
            side_effect=ValueError("bad UUID")
        )

        session = MockSession()
        node = _make_action_node(
            session.flow_id,
            {
                "actions": [
                    {
                        "type": "api_call",
                        "config": {
                            "endpoint": "/v1/recommend",
                            "auth_type": "internal",
                            "body": {},
                            "response_mapping": {},
                        },
                    }
                ]
            },
        )

        result = await action_processor.process(
            mock_db, node, session, {"db": mock_db}
        )
        # The outer _execute_actions_sync catches the exception and sets success=False
        assert result["success"] is False

    @pytest.mark.asyncio
    @patch("app.services.chat_runtime.chat_repo")
    @patch("app.services.action_processor.chat_repo")
    @patch("app.services.internal_api_handlers.INTERNAL_HANDLERS", new_callable=dict)
    async def test_template_stripping_applied_to_body_and_params(
        self,
        mock_handlers,
        mock_action_chat_repo,
        mock_runtime_chat_repo,
        action_processor,
        mock_db,
    ):
        """Unresolved templates in body and query_params are stripped to None."""
        _setup_chat_repo(mock_action_chat_repo)
        _setup_chat_repo(mock_runtime_chat_repo)

        captured_args = {}

        async def capture_handler(db, body, params):
            captured_args["body"] = body
            captured_args["params"] = params
            return {"result": "ok"}

        mock_handlers["/v1/test"] = capture_handler

        session = MockSession()
        node = _make_action_node(
            session.flow_id,
            {
                "actions": [
                    {
                        "type": "api_call",
                        "config": {
                            "endpoint": "/v1/test",
                            "auth_type": "internal",
                            "body": {
                                "name": "resolved",
                                "school_id": "{{context.school_wriveted_id}}",
                            },
                            "query_params": {
                                "limit": 10,
                                "filter": "{{context.missing}}",
                            },
                            "response_mapping": {},
                        },
                    }
                ]
            },
        )

        result = await action_processor.process(
            mock_db, node, session, {"db": mock_db}
        )

        assert result["success"] is True
        assert captured_args["body"] == {"name": "resolved", "school_id": None}
        assert captured_args["params"] == {"limit": 10, "filter": None}
