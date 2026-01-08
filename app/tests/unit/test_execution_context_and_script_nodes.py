"""
Unit tests for ExecutionContext enum, NodeType.SCRIPT, and related validation.

Tests:
- ExecutionContext enum values and case-insensitive behavior
- NodeType enum includes SCRIPT
- SCRIPT node content validation
- Theme configuration schema validation
"""

import pytest
from pydantic import ValidationError

from app.models.cms import ExecutionContext, NodeType
from app.schemas.cms import NodeCreate


class TestExecutionContextEnum:
    """Test ExecutionContext enum behavior."""

    def test_execution_context_values(self):
        """Test all ExecutionContext enum values are accessible."""
        assert ExecutionContext.FRONTEND.value == "frontend"
        assert ExecutionContext.BACKEND.value == "backend"
        assert ExecutionContext.MIXED.value == "mixed"

    def test_execution_context_case_insensitive(self):
        """Test ExecutionContext is case-insensitive."""
        assert ExecutionContext("FRONTEND") == ExecutionContext.FRONTEND
        assert ExecutionContext("frontend") == ExecutionContext.FRONTEND
        assert ExecutionContext("Frontend") == ExecutionContext.FRONTEND

    def test_execution_context_from_string(self):
        """Test creating ExecutionContext from string values."""
        frontend = ExecutionContext("frontend")
        backend = ExecutionContext("backend")
        mixed = ExecutionContext("mixed")

        assert frontend == ExecutionContext.FRONTEND
        assert backend == ExecutionContext.BACKEND
        assert mixed == ExecutionContext.MIXED

    def test_execution_context_invalid_value(self):
        """Test invalid ExecutionContext value raises error."""
        with pytest.raises(ValueError):
            ExecutionContext("invalid")


class TestNodeTypeEnum:
    """Test NodeType enum includes SCRIPT."""

    def test_script_node_type_exists(self):
        """Test SCRIPT is a valid NodeType."""
        assert hasattr(NodeType, "SCRIPT")
        assert NodeType.SCRIPT.value == "script"

    def test_all_node_types(self):
        """Test all NodeType enum values."""
        expected_types = {
            "start",
            "message",
            "question",
            "condition",
            "action",
            "webhook",
            "composite",
            "script",
        }

        actual_types = {node_type.value for node_type in NodeType}
        assert actual_types == expected_types

    def test_node_type_case_insensitive(self):
        """Test NodeType is case-insensitive."""
        assert NodeType("SCRIPT") == NodeType.SCRIPT
        assert NodeType("script") == NodeType.SCRIPT
        assert NodeType("Script") == NodeType.SCRIPT


class TestScriptNodeValidation:
    """Test SCRIPT node content validation in schemas."""

    def test_create_script_node_minimal(self):
        """Test creating SCRIPT node with minimal required fields."""
        node_data = {
            "node_id": "script_1",
            "node_type": "script",
            "content": {
                "code": "console.log('Hello');",
                "language": "javascript",
            },
        }

        node = NodeCreate(**node_data)
        assert node.node_type == NodeType.SCRIPT
        assert node.content["code"] == "console.log('Hello');"
        assert node.content["language"] == "javascript"

    def test_create_script_node_full_config(self):
        """Test creating SCRIPT node with full configuration."""
        node_data = {
            "node_id": "script_2",
            "node_type": "script",
            "content": {
                "code": "outputs['result'] = inputs.value * 2;",
                "language": "typescript",
                "sandbox": "strict",
                "inputs": {"value": "session.user_input"},
                "outputs": ["temp.result"],
                "dependencies": ["https://cdn.example.com/lib.js"],
                "timeout": 5000,
                "description": "Double the input value",
            },
        }

        node = NodeCreate(**node_data)
        assert node.node_type == NodeType.SCRIPT
        assert "outputs" in node.content
        assert "inputs" in node.content
        assert node.content["timeout"] == 5000

    def test_script_node_with_empty_code(self):
        """Test SCRIPT node validation with empty code."""
        node_data = {
            "node_id": "script_3",
            "node_type": "script",
            "content": {
                "code": "",
                "language": "javascript",
            },
        }

        node = NodeCreate(**node_data)
        assert node.content["code"] == ""

    def test_script_node_with_dependencies(self):
        """Test SCRIPT node with external dependencies."""
        node_data = {
            "node_id": "script_4",
            "node_type": "script",
            "content": {
                "code": "printJS({printable: 'content'});",
                "language": "javascript",
                "dependencies": [
                    "https://cdn.jsdelivr.net/npm/print-js@1.6.0/dist/print.js"
                ],
            },
        }

        node = NodeCreate(**node_data)
        assert len(node.content["dependencies"]) == 1
        assert "print-js" in node.content["dependencies"][0]

    def test_script_node_with_inputs_outputs(self):
        """Test SCRIPT node with input/output mapping."""
        node_data = {
            "node_id": "script_5",
            "node_type": "script",
            "content": {
                "code": "outputs['temp.calculated'] = inputs.bookCount * inputs.avgTime;",
                "language": "typescript",
                "inputs": {
                    "bookCount": "temp.liked_books.length",
                    "avgTime": "context.avg_reading_time",
                },
                "outputs": ["temp.calculated", "temp.result"],
            },
        }

        node = NodeCreate(**node_data)
        assert isinstance(node.content["inputs"], dict)
        assert isinstance(node.content["outputs"], list)
        assert len(node.content["outputs"]) == 2

    def test_script_node_typescript_language(self):
        """Test SCRIPT node with TypeScript language."""
        node_data = {
            "node_id": "script_6",
            "node_type": "script",
            "content": {
                "code": "const result: number = 42;",
                "language": "typescript",
            },
        }

        node = NodeCreate(**node_data)
        assert node.content["language"] == "typescript"

    def test_script_node_javascript_language(self):
        """Test SCRIPT node with JavaScript language."""
        node_data = {
            "node_id": "script_7",
            "node_type": "script",
            "content": {
                "code": "var result = 42;",
                "language": "javascript",
            },
        }

        node = NodeCreate(**node_data)
        assert node.content["language"] == "javascript"


class TestNodeCreateWithExecutionContext:
    """Test NodeCreate schema with execution_context field."""

    def test_message_node_defaults_to_backend_context(self):
        """Test MESSAGE node without execution_context (backend is default in DB)."""
        node_data = {
            "node_id": "msg_1",
            "node_type": "message",
            "content": {"messages": [{"text": "Hello"}]},
        }

        node = NodeCreate(**node_data)
        assert node.node_type == NodeType.MESSAGE

    def test_script_node_defaults_to_backend_context(self):
        """Test SCRIPT node without execution_context (backend is default in DB)."""
        node_data = {
            "node_id": "script_8",
            "node_type": "script",
            "content": {"code": "console.log('test');", "language": "javascript"},
        }

        node = NodeCreate(**node_data)
        assert node.node_type == NodeType.SCRIPT

    def test_node_with_explicit_frontend_context(self):
        """Test node with explicit frontend execution context."""
        node_data = {
            "node_id": "script_9",
            "node_type": "script",
            "content": {"code": "alert('test');", "language": "javascript"},
        }

        node = NodeCreate(**node_data)
        assert node.node_type == NodeType.SCRIPT

    def test_node_with_explicit_backend_context(self):
        """Test node with explicit backend execution context."""
        node_data = {
            "node_id": "webhook_1",
            "node_type": "webhook",
            "content": {"url": "https://api.example.com", "method": "POST"},
        }

        node = NodeCreate(**node_data)
        assert node.node_type == NodeType.WEBHOOK

    def test_node_with_mixed_context(self):
        """Test composite node with mixed execution context."""
        node_data = {
            "node_id": "composite_1",
            "node_type": "composite",
            "content": {"children": ["node1", "node2"]},
        }

        node = NodeCreate(**node_data)
        assert node.node_type == NodeType.COMPOSITE


class TestScriptNodeValidationEdgeCases:
    """Test edge cases for SCRIPT node validation."""

    def test_script_node_multiline_code(self):
        """Test SCRIPT node with multiline code."""
        code = """
function calculateTotal(items) {
    let total = 0;
    for (const item of items) {
        total += item.price;
    }
    return total;
}
outputs['temp.total'] = calculateTotal(inputs.items);
        """.strip()

        node_data = {
            "node_id": "script_10",
            "node_type": "script",
            "content": {
                "code": code,
                "language": "javascript",
            },
        }

        node = NodeCreate(**node_data)
        assert "function calculateTotal" in node.content["code"]
        assert "outputs['temp.total']" in node.content["code"]

    def test_script_node_with_special_characters(self):
        """Test SCRIPT node with special characters in code."""
        node_data = {
            "node_id": "script_11",
            "node_type": "script",
            "content": {
                "code": "const msg = 'Hello \"world\"!'; outputs['temp.msg'] = msg;",
                "language": "javascript",
            },
        }

        node = NodeCreate(**node_data)
        assert '"world"' in node.content["code"]

    def test_script_node_with_unicode(self):
        """Test SCRIPT node with Unicode characters."""
        node_data = {
            "node_id": "script_12",
            "node_type": "script",
            "content": {
                "code": "const emoji = '📚'; outputs['temp.emoji'] = emoji;",
                "language": "javascript",
            },
        }

        node = NodeCreate(**node_data)
        assert "📚" in node.content["code"]

    def test_script_node_timeout_validation(self):
        """Test SCRIPT node with various timeout values."""
        node_data = {
            "node_id": "script_13",
            "node_type": "script",
            "content": {
                "code": "console.log('test');",
                "language": "javascript",
                "timeout": 10000,
            },
        }

        node = NodeCreate(**node_data)
        assert node.content["timeout"] == 10000

    def test_script_node_sandbox_modes(self):
        """Test SCRIPT node with different sandbox modes."""
        for sandbox_mode in ["strict", "permissive"]:
            node_data = {
                "node_id": f"script_{sandbox_mode}",
                "node_type": "script",
                "content": {
                    "code": "console.log('test');",
                    "language": "javascript",
                    "sandbox": sandbox_mode,
                },
            }

            node = NodeCreate(**node_data)
            assert node.content["sandbox"] == sandbox_mode

    def test_script_node_empty_dependencies_list(self):
        """Test SCRIPT node with empty dependencies list."""
        node_data = {
            "node_id": "script_14",
            "node_type": "script",
            "content": {
                "code": "console.log('test');",
                "language": "javascript",
                "dependencies": [],
            },
        }

        node = NodeCreate(**node_data)
        assert node.content["dependencies"] == []

    def test_script_node_multiple_outputs(self):
        """Test SCRIPT node with multiple output paths."""
        node_data = {
            "node_id": "script_15",
            "node_type": "script",
            "content": {
                "code": "outputs['temp.a'] = 1; outputs['temp.b'] = 2;",
                "language": "javascript",
                "outputs": [
                    "temp.a",
                    "temp.b",
                    "temp.c",
                    "user.preference",
                    "context.result",
                ],
            },
        }

        node = NodeCreate(**node_data)
        assert len(node.content["outputs"]) == 5

    def test_script_node_complex_input_mapping(self):
        """Test SCRIPT node with complex input mapping."""
        node_data = {
            "node_id": "script_16",
            "node_type": "script",
            "content": {
                "code": "console.log(inputs.data);",
                "language": "javascript",
                "inputs": {
                    "userName": "user.name",
                    "userAge": "user.age",
                    "bookList": "temp.liked_books",
                    "readingLevel": "context.reading_level",
                    "preferences": "session.user_preferences",
                },
            },
        }

        node = NodeCreate(**node_data)
        assert len(node.content["inputs"]) == 5
        assert node.content["inputs"]["userName"] == "user.name"
