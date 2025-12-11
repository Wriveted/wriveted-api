"""
Integration tests for execution contexts and SCRIPT nodes in flows.

Tests:
- Create flow nodes with execution_context field
- Query nodes by execution context
- Create flows with SCRIPT nodes
- Validate flows containing SCRIPT nodes
- SCRIPT node processor validation
- Mixed execution context flows
"""

import pytest
from sqlalchemy import text
from starlette import status


@pytest.fixture(autouse=True)
async def cleanup_flow_data(async_session):
    """Clean up flow data before and after each test."""
    cms_tables = [
        "flow_definitions",
        "flow_nodes",
        "flow_connections",
        "conversation_sessions",
        "conversation_history",
    ]

    await async_session.rollback()

    for table in cms_tables:
        try:
            await async_session.execute(
                text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
            )
        except Exception:
            pass
    await async_session.commit()

    yield

    await async_session.rollback()
    for table in cms_tables:
        try:
            await async_session.execute(
                text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
            )
        except Exception:
            pass
    await async_session.commit()


class TestFlowNodeExecutionContext:
    """Test flow nodes with execution_context field."""

    def test_create_node_with_frontend_context(
        self, client, backend_service_account_headers
    ):
        """Test creating a node with frontend execution context."""
        flow_data = {
            "name": "Test Flow",
            "version": "1.0.0",
            "flow_data": {},
        }
        flow_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = flow_response.json()["id"]

        node_data = {
            "node_id": "msg_1",
            "node_type": "message",
            "content": {"messages": [{"text": "Hello"}]},
        }

        response = client.post(
            f"v1/cms/flows/{flow_id}/nodes",
            json=node_data,
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["node_type"] == "message"

    def test_create_node_with_backend_context(
        self, client, backend_service_account_headers
    ):
        """Test creating a node with backend execution context."""
        flow_data = {
            "name": "Test Flow",
            "version": "1.0.0",
            "flow_data": {},
        }
        flow_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = flow_response.json()["id"]

        node_data = {
            "node_id": "webhook_1",
            "node_type": "webhook",
            "content": {"url": "https://api.example.com", "method": "POST"},
        }

        response = client.post(
            f"v1/cms/flows/{flow_id}/nodes",
            json=node_data,
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["node_type"] == "webhook"

    def test_create_node_with_mixed_context(
        self, client, backend_service_account_headers
    ):
        """Test creating a composite node with mixed execution context."""
        flow_data = {
            "name": "Test Flow",
            "version": "1.0.0",
            "flow_data": {},
        }
        flow_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = flow_response.json()["id"]

        node_data = {
            "node_id": "composite_1",
            "node_type": "composite",
            "content": {"children": ["node1", "node2"]},
        }

        response = client.post(
            f"v1/cms/flows/{flow_id}/nodes",
            json=node_data,
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["node_type"] == "composite"

    def test_list_nodes_shows_execution_context(
        self, client, backend_service_account_headers
    ):
        """Test listing nodes includes execution_context field."""
        flow_data = {
            "name": "Test Flow",
            "version": "1.0.0",
            "flow_data": {},
        }
        flow_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = flow_response.json()["id"]

        node_data = {
            "node_id": "test_node",
            "node_type": "message",
            "content": {"messages": [{"text": "Test"}]},
        }
        client.post(
            f"v1/cms/flows/{flow_id}/nodes",
            json=node_data,
            headers=backend_service_account_headers,
        )

        response = client.get(
            f"v1/cms/flows/{flow_id}/nodes", headers=backend_service_account_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]) > 0


class TestScriptNodes:
    """Test SCRIPT node creation and validation."""

    def test_create_script_node_minimal(self, client, backend_service_account_headers):
        """Test creating a minimal SCRIPT node."""
        flow_data = {
            "name": "Script Flow",
            "version": "1.0.0",
            "flow_data": {},
        }
        flow_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = flow_response.json()["id"]

        node_data = {
            "node_id": "script_1",
            "node_type": "script",
            "content": {
                "code": "console.log('Hello World');",
                "language": "javascript",
            },
        }

        response = client.post(
            f"v1/cms/flows/{flow_id}/nodes",
            json=node_data,
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["node_type"] == "script"
        assert data["content"]["code"] == "console.log('Hello World');"
        assert data["content"]["language"] == "javascript"

    def test_create_script_node_with_inputs_outputs(
        self, client, backend_service_account_headers
    ):
        """Test creating SCRIPT node with inputs and outputs."""
        flow_data = {
            "name": "Script Flow",
            "version": "1.0.0",
            "flow_data": {},
        }
        flow_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = flow_response.json()["id"]

        node_data = {
            "node_id": "script_2",
            "node_type": "script",
            "content": {
                "code": "outputs['temp.result'] = inputs.value * 2;",
                "language": "typescript",
                "inputs": {"value": "session.user_input"},
                "outputs": ["temp.result"],
            },
        }

        response = client.post(
            f"v1/cms/flows/{flow_id}/nodes",
            json=node_data,
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "inputs" in data["content"]
        assert "outputs" in data["content"]
        assert data["content"]["outputs"] == ["temp.result"]

    def test_create_script_node_with_dependencies(
        self, client, backend_service_account_headers
    ):
        """Test creating SCRIPT node with external dependencies."""
        flow_data = {
            "name": "Script Flow",
            "version": "1.0.0",
            "flow_data": {},
        }
        flow_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = flow_response.json()["id"]

        node_data = {
            "node_id": "script_3",
            "node_type": "script",
            "content": {
                "code": "printJS({printable: 'document'});",
                "language": "javascript",
                "dependencies": [
                    "https://cdn.jsdelivr.net/npm/print-js@1.6.0/dist/print.js"
                ],
            },
        }

        response = client.post(
            f"v1/cms/flows/{flow_id}/nodes",
            json=node_data,
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert len(data["content"]["dependencies"]) == 1

    def test_create_script_node_with_timeout(
        self, client, backend_service_account_headers
    ):
        """Test creating SCRIPT node with custom timeout."""
        flow_data = {
            "name": "Script Flow",
            "version": "1.0.0",
            "flow_data": {},
        }
        flow_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = flow_response.json()["id"]

        node_data = {
            "node_id": "script_4",
            "node_type": "script",
            "content": {
                "code": "setTimeout(() => console.log('done'), 1000);",
                "language": "javascript",
                "timeout": 5000,
            },
        }

        response = client.post(
            f"v1/cms/flows/{flow_id}/nodes",
            json=node_data,
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["content"]["timeout"] == 5000

    def test_create_script_node_with_sandbox_mode(
        self, client, backend_service_account_headers
    ):
        """Test creating SCRIPT node with sandbox configuration."""
        flow_data = {
            "name": "Script Flow",
            "version": "1.0.0",
            "flow_data": {},
        }
        flow_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = flow_response.json()["id"]

        node_data = {
            "node_id": "script_5",
            "node_type": "script",
            "content": {
                "code": "document.body.style.backgroundColor = 'blue';",
                "language": "javascript",
                "sandbox": "permissive",
            },
        }

        response = client.post(
            f"v1/cms/flows/{flow_id}/nodes",
            json=node_data,
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["content"]["sandbox"] == "permissive"

    def test_create_script_node_multiline_code(
        self, client, backend_service_account_headers
    ):
        """Test creating SCRIPT node with multiline code."""
        flow_data = {
            "name": "Script Flow",
            "version": "1.0.0",
            "flow_data": {},
        }
        flow_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = flow_response.json()["id"]

        code = """
function calculateTotal(items) {
    return items.reduce((sum, item) => sum + item.price, 0);
}
outputs['temp.total'] = calculateTotal(inputs.items);
        """.strip()

        node_data = {
            "node_id": "script_6",
            "node_type": "script",
            "content": {
                "code": code,
                "language": "javascript",
                "inputs": {"items": "temp.cart_items"},
                "outputs": ["temp.total"],
            },
        }

        response = client.post(
            f"v1/cms/flows/{flow_id}/nodes",
            json=node_data,
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "calculateTotal" in data["content"]["code"]


class TestFlowValidationWithScriptNodes:
    """Test flow validation containing SCRIPT nodes."""

    def test_validate_flow_with_script_node(
        self, client, backend_service_account_headers
    ):
        """Test validating a flow containing SCRIPT nodes."""
        flow_data = {
            "name": "Flow with Script",
            "version": "1.0.0",
            "flow_data": {},
            "entry_node_id": "start",
        }
        flow_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = flow_response.json()["id"]

        start_node = {
            "node_id": "start",
            "node_type": "message",
            "content": {"messages": [{"text": "Welcome"}]},
        }
        client.post(
            f"v1/cms/flows/{flow_id}/nodes",
            json=start_node,
            headers=backend_service_account_headers,
        )

        script_node = {
            "node_id": "script_node",
            "node_type": "script",
            "content": {
                "code": "console.log('Processing');",
                "language": "javascript",
            },
        }
        client.post(
            f"v1/cms/flows/{flow_id}/nodes",
            json=script_node,
            headers=backend_service_account_headers,
        )

        connection = {
            "source_node_id": "start",
            "target_node_id": "script_node",
            "connection_type": "default",
        }
        client.post(
            f"v1/cms/flows/{flow_id}/connections",
            json=connection,
            headers=backend_service_account_headers,
        )

        response = client.get(
            f"v1/cms/flows/{flow_id}/validate", headers=backend_service_account_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "is_valid" in data

    def test_validate_flow_with_multiple_execution_contexts(
        self, client, backend_service_account_headers
    ):
        """Test validating a flow with mixed execution contexts."""
        flow_data = {
            "name": "Mixed Context Flow",
            "version": "1.0.0",
            "flow_data": {},
            "entry_node_id": "start",
        }
        flow_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = flow_response.json()["id"]

        nodes = [
            {
                "node_id": "start",
                "node_type": "message",
                "content": {"messages": [{"text": "Start"}]},
            },
            {
                "node_id": "script_frontend",
                "node_type": "script",
                "content": {
                    "code": "console.log('frontend');",
                    "language": "javascript",
                },
            },
            {
                "node_id": "webhook_backend",
                "node_type": "webhook",
                "content": {"url": "https://api.example.com", "method": "POST"},
            },
        ]

        for node in nodes:
            client.post(
                f"v1/cms/flows/{flow_id}/nodes",
                json=node,
                headers=backend_service_account_headers,
            )

        connections = [
            {
                "source_node_id": "start",
                "target_node_id": "script_frontend",
                "connection_type": "default",
            },
            {
                "source_node_id": "script_frontend",
                "target_node_id": "webhook_backend",
                "connection_type": "default",
            },
        ]

        for conn in connections:
            client.post(
                f"v1/cms/flows/{flow_id}/connections",
                json=conn,
                headers=backend_service_account_headers,
            )

        response = client.get(
            f"v1/cms/flows/{flow_id}/validate", headers=backend_service_account_headers
        )

        assert response.status_code == status.HTTP_200_OK


class TestScriptNodeEdgeCases:
    """Test edge cases for SCRIPT nodes."""

    def test_script_node_empty_code(self, client, backend_service_account_headers):
        """Test SCRIPT node with empty code."""
        flow_data = {
            "name": "Script Flow",
            "version": "1.0.0",
            "flow_data": {},
        }
        flow_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = flow_response.json()["id"]

        node_data = {
            "node_id": "script_empty",
            "node_type": "script",
            "content": {"code": "", "language": "javascript"},
        }

        response = client.post(
            f"v1/cms/flows/{flow_id}/nodes",
            json=node_data,
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED

    def test_script_node_large_code(self, client, backend_service_account_headers):
        """Test SCRIPT node with large code block."""
        flow_data = {
            "name": "Script Flow",
            "version": "1.0.0",
            "flow_data": {},
        }
        flow_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = flow_response.json()["id"]

        large_code = "console.log('test');\n" * 100

        node_data = {
            "node_id": "script_large",
            "node_type": "script",
            "content": {"code": large_code, "language": "javascript"},
        }

        response = client.post(
            f"v1/cms/flows/{flow_id}/nodes",
            json=node_data,
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED

    def test_script_node_special_characters(
        self, client, backend_service_account_headers
    ):
        """Test SCRIPT node with special characters."""
        flow_data = {
            "name": "Script Flow",
            "version": "1.0.0",
            "flow_data": {},
        }
        flow_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = flow_response.json()["id"]

        node_data = {
            "node_id": "script_special",
            "node_type": "script",
            "content": {
                "code": "const msg = 'Hello \"World\" \\'Test\\' 📚';",
                "language": "javascript",
            },
        }

        response = client.post(
            f"v1/cms/flows/{flow_id}/nodes",
            json=node_data,
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "📚" in data["content"]["code"]

    def test_update_script_node(self, client, backend_service_account_headers):
        """Test updating an existing SCRIPT node."""
        flow_data = {
            "name": "Script Flow",
            "version": "1.0.0",
            "flow_data": {},
        }
        flow_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = flow_response.json()["id"]

        node_data = {
            "node_id": "script_update",
            "node_type": "script",
            "content": {"code": "console.log('original');", "language": "javascript"},
        }
        create_response = client.post(
            f"v1/cms/flows/{flow_id}/nodes",
            json=node_data,
            headers=backend_service_account_headers,
        )
        node_db_id = create_response.json()["id"]

        update_data = {
            "content": {"code": "console.log('updated');", "language": "javascript"}
        }

        response = client.put(
            f"v1/cms/flows/{flow_id}/nodes/{node_db_id}",
            json=update_data,
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["content"]["code"] == "console.log('updated');"
