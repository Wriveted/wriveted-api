"""
Comprehensive CMS Flow Management Tests.

This module consolidates all flow-related tests from multiple CMS test files:
- Flow CRUD operations (create, read, update, delete)
- Flow publishing and versioning workflows
- Flow cloning and duplication functionality
- Flow node management (create, update, delete nodes)
- Flow connection management between nodes
- Flow validation and integrity checks
- Flow import/export functionality

Consolidated from:
- test_cms.py (flow management, nodes, connections)
- test_cms_api_enhanced.py (complex flow creation)
- test_cms_authenticated.py (authenticated flow operations)
- test_cms_full_integration.py (flow API integration tests)
"""

import uuid

import pytest
from sqlalchemy import text
from starlette import status


@pytest.fixture(autouse=True)
async def cleanup_cms_data(async_session):
    """Clean up CMS data before and after each test to ensure test isolation."""
    cms_tables = [
        "cms_content",
        "cms_content_variants",
        "flow_definitions",
        "flow_nodes",
        "flow_connections",
        "conversation_sessions",
        "conversation_history",
        "conversation_analytics",
    ]

    await async_session.rollback()

    # Clean up before test runs
    for table in cms_tables:
        try:
            await async_session.execute(
                text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
            )
        except Exception:
            # Table might not exist, skip it
            pass
    await async_session.commit()

    yield

    await async_session.rollback()

    # Clean up after test runs
    for table in cms_tables:
        try:
            await async_session.execute(
                text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
            )
        except Exception:
            # Table might not exist, skip it
            pass
    await async_session.commit()


class TestFlowCRUD:
    """Test basic flow CRUD operations."""

    def test_create_flow_basic(self, client, backend_service_account_headers):
        """Test creating a basic flow definition."""
        flow_data = {
            "name": "Basic Welcome Flow",
            "description": "A simple welcome flow for new users",
            "version": "1.0.0",
            "flow_data": {
                "entry_point": "start_node",
                "variables": ["user_name", "user_age"],
                "settings": {"timeout": 300, "max_retries": 3},
            },
            "entry_node_id": "start_node",
            "info": {"category": "onboarding", "target_audience": "general"},
        }

        response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Basic Welcome Flow"
        assert data["version"] == "1.0.0"
        assert data["entry_node_id"] == "start_node"
        assert data["is_published"] is False
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data

    def test_create_flow_complex(self, client, backend_service_account_headers):
        """Test creating a complex flow with multiple configurations."""
        flow_data = {
            "name": "Book Recommendation Flow",
            "description": "Advanced flow for personalized book recommendations",
            "version": "2.1.0",
            "flow_data": {
                "entry_point": "welcome_node",
                "variables": [
                    "user_age",
                    "reading_level",
                    "favorite_genres",
                    "reading_goals",
                    "book_preferences",
                ],
                "settings": {
                    "timeout": 600,
                    "max_retries": 5,
                    "fallback_flow": "simple_recommendation_flow",
                    "analytics_enabled": True,
                },
                "conditional_logic": {
                    "age_branching": {
                        "children": {"max_age": 12, "flow": "children_flow"},
                        "teens": {"min_age": 13, "max_age": 17, "flow": "teen_flow"},
                        "adults": {"min_age": 18, "flow": "adult_flow"},
                    }
                },
            },
            "entry_node_id": "welcome_node",
            "info": {
                "category": "recommendation",
                "target_audience": "all_ages",
                "complexity": "advanced",
                "estimated_duration": "5-10 minutes",
                "required_permissions": ["read_user_profile", "access_book_catalog"],
            },
        }

        response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Book Recommendation Flow"
        assert len(data["flow_data"]["variables"]) == 5
        assert data["info"]["complexity"] == "advanced"
        assert data["flow_data"]["settings"]["analytics_enabled"] is True

    def test_get_flow_by_id(self, client, backend_service_account_headers):
        """Test retrieving specific flow by ID."""
        # First create flow
        flow_data = {
            "name": "Test Flow for Retrieval",
            "description": "Flow created for testing GET operation",
            "version": "1.0.0",
            "flow_data": {"entry_point": "start"},
            "entry_node_id": "start",
        }

        create_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = create_response.json()["id"]

        # Get the flow
        response = client.get(
            f"v1/cms/flows/{flow_id}", headers=backend_service_account_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == flow_id
        assert data["name"] == "Test Flow for Retrieval"
        assert data["version"] == "1.0.0"

    def test_get_nonexistent_flow(self, client, backend_service_account_headers):
        """Test retrieving non-existent flow returns 404."""
        fake_id = str(uuid.uuid4())
        response = client.get(
            f"v1/cms/flows/{fake_id}", headers=backend_service_account_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_flow(self, client, backend_service_account_headers):
        """Test updating existing flow."""
        # Create flow first
        flow_data = {
            "name": "Flow to Update",
            "description": "Original description",
            "version": "1.0.0",
            "flow_data": {"entry_point": "start"},
            "entry_node_id": "start",
        }

        create_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = create_response.json()["id"]

        # Update the flow
        update_data = {
            "name": "Updated Flow Name",
            "description": "Updated description with more details",
            "version": "1.1.0",
            "flow_data": {
                "entry_point": "updated_start",
                "variables": ["new_variable"],
                "settings": {"timeout": 400},
            },
            "entry_node_id": "updated_start",
            "info": {
                "category": "updated",
                "last_modified_reason": "Added new features",
            },
        }

        response = client.put(
            f"v1/cms/flows/{flow_id}",
            json=update_data,
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Flow Name"
        assert data["version"] == "1.1.0"
        assert data["entry_node_id"] == "updated_start"
        assert data["info"]["category"] == "updated"

    def test_update_nonexistent_flow(self, client, backend_service_account_headers):
        """Test updating non-existent flow returns 404."""
        fake_id = str(uuid.uuid4())
        update_data = {"name": "Updated Name"}

        response = client.put(
            f"v1/cms/flows/{fake_id}",
            json=update_data,
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_flow(self, client, backend_service_account_headers):
        """Test soft deletion of flow."""
        # Create flow first
        flow_data = {
            "name": "Flow to Delete",
            "version": "1.0.0",
            "flow_data": {"entry_point": "start"},
            "entry_node_id": "start",
        }

        create_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = create_response.json()["id"]

        # Delete the flow
        response = client.delete(
            f"v1/cms/flows/{flow_id}", headers=backend_service_account_headers
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify flow is soft deleted
        get_response = client.get(
            f"v1/cms/flows/{flow_id}", headers=backend_service_account_headers
        )
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

        # But should be available when including inactive
        get_inactive_response = client.get(
            f"v1/cms/flows/{flow_id}?include_inactive=true",
            headers=backend_service_account_headers,
        )
        assert get_inactive_response.status_code == status.HTTP_200_OK
        data = get_inactive_response.json()
        assert data["is_active"] is False

    def test_delete_nonexistent_flow(self, client, backend_service_account_headers):
        """Test deleting non-existent flow returns 404."""
        fake_id = str(uuid.uuid4())
        response = client.delete(
            f"v1/cms/flows/{fake_id}", headers=backend_service_account_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestFlowListing:
    """Test flow listing, filtering, and search functionality."""

    def test_list_all_flows(self, client, backend_service_account_headers):
        """Test listing all flows with pagination."""
        response = client.get("v1/cms/flows", headers=backend_service_account_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)

    def test_filter_flows_by_published_status(
        self, client, backend_service_account_headers
    ):
        """Test filtering flows by publication status."""
        # Test published flows
        response = client.get(
            "v1/cms/flows?is_published=true", headers=backend_service_account_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for flow in data["data"]:
            assert flow["is_published"] is True

        # Test unpublished flows
        response = client.get(
            "v1/cms/flows?is_published=false", headers=backend_service_account_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for flow in data["data"]:
            assert flow["is_published"] is False

    def test_search_flows_by_name(self, client, backend_service_account_headers):
        """Test searching flows by name."""
        response = client.get(
            "v1/cms/flows?search=welcome", headers=backend_service_account_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for flow in data["data"]:
            flow_text = f"{flow['name']} {flow.get('description', '')}".lower()
            assert "welcome" in flow_text

    def test_filter_flows_by_version(self, client, backend_service_account_headers):
        """Test filtering flows by version pattern."""
        response = client.get(
            "v1/cms/flows?version=1.0.0", headers=backend_service_account_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for flow in data["data"]:
            assert flow["version"] == "1.0.0"

    def test_pagination_flows(self, client, backend_service_account_headers):
        """Test flow pagination."""
        response = client.get(
            "v1/cms/flows?limit=2", headers=backend_service_account_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]) <= 2
        assert data["pagination"]["limit"] == 2


class TestFlowPublishing:
    """Test flow publishing and versioning workflows."""

    def test_publish_flow(self, client, backend_service_account_headers):
        """Test publishing a flow."""
        # Create flow first with proper nodes
        flow_data = {
            "name": "Flow to Publish",
            "version": "1.0.0",
            "flow_data": {
                "nodes": [
                    {
                        "id": "start",
                        "type": "start",
                        "data": {"name": "Start Node", "message": "Welcome"},
                        "position": {"x": 100, "y": 100},
                    }
                ],
                "connections": [],
            },
            "entry_node_id": "start",
        }

        create_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = create_response.json()["id"]

        # Publish the flow
        response = client.post(
            f"v1/cms/flows/{flow_id}/publish",
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_published"] is True
        assert data["published_at"] is not None

    def test_unpublish_flow(self, client, backend_service_account_headers):
        """Test unpublishing a flow."""
        # Create and publish flow first
        flow_data = {
            "name": "Flow to Unpublish",
            "version": "1.0.0",
            "flow_data": {"entry_point": "start"},
            "entry_node_id": "start",
        }

        create_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = create_response.json()["id"]

        # Publish first
        client.post(
            f"v1/cms/flows/{flow_id}/publish",
            headers=backend_service_account_headers,
        )

        # Then unpublish
        response = client.post(
            f"v1/cms/flows/{flow_id}/unpublish",
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_published"] is False

    def test_publish_nonexistent_flow(self, client, backend_service_account_headers):
        """Test publishing non-existent flow returns 404."""
        fake_id = str(uuid.uuid4())
        response = client.post(
            f"v1/cms/flows/{fake_id}/publish",
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_flow_version_increment_on_publish(
        self, client, backend_service_account_headers
    ):
        """Test that flow version can be incremented when publishing."""
        # Create flow with proper nodes
        flow_data = {
            "name": "Versioned Flow",
            "version": "1.0.0",
            "flow_data": {
                "nodes": [
                    {
                        "id": "start",
                        "type": "start",
                        "data": {
                            "name": "Start Node",
                            "message": "Welcome to versioned flow",
                        },
                        "position": {"x": 100, "y": 100},
                    }
                ],
                "connections": [],
            },
            "entry_node_id": "start",
        }

        create_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = create_response.json()["id"]

        # Publish with version increment
        publish_data = {"increment_version": True, "version_type": "minor"}
        response = client.post(
            f"v1/cms/flows/{flow_id}/publish",
            json=publish_data,
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_published"] is True
        assert data["version"] == "1.1.0"


class TestFlowCloning:
    """Test flow cloning and duplication functionality."""

    def test_clone_flow(self, client, backend_service_account_headers):
        """Test cloning an existing flow."""
        # Create original flow
        flow_data = {
            "name": "Original Flow",
            "description": "Original flow for cloning",
            "version": "1.0.0",
            "flow_data": {
                "entry_point": "start",
                "variables": ["var1", "var2"],
                "settings": {"timeout": 300},
            },
            "entry_node_id": "start",
            "info": {"category": "original"},
        }

        create_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        original_flow_id = create_response.json()["id"]

        # Clone the flow
        clone_data = {
            "name": "Cloned Flow",
            "description": "Cloned from original",
            "version": "1.0.0",
            "clone_nodes": True,
            "clone_connections": True,
        }

        response = client.post(
            f"v1/cms/flows/{original_flow_id}/clone",
            json=clone_data,
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Cloned Flow"
        assert data["description"] == "Cloned from original"
        assert data["flow_data"]["variables"] == ["var1", "var2"]
        assert data["id"] != original_flow_id  # Should be different ID
        assert data["is_published"] is False  # Clones start unpublished

    def test_clone_flow_with_custom_settings(
        self, client, backend_service_account_headers
    ):
        """Test cloning with custom modifications."""
        # Create original flow
        flow_data = {
            "name": "Source Flow",
            "version": "2.0.0",
            "flow_data": {"entry_point": "start"},
            "entry_node_id": "start",
        }

        create_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        original_flow_id = create_response.json()["id"]

        # Clone with modifications
        clone_data = {
            "name": "Modified Clone",
            "version": "2.1.0",
            "clone_nodes": False,  # Don't clone nodes
            "clone_connections": False,  # Don't clone connections
            "info": {"category": "modified", "original_flow_id": original_flow_id},
        }

        response = client.post(
            f"v1/cms/flows/{original_flow_id}/clone",
            json=clone_data,
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Modified Clone"
        assert data["version"] == "2.1.0"
        assert data["info"]["category"] == "modified"

    def test_clone_nonexistent_flow(self, client, backend_service_account_headers):
        """Test cloning non-existent flow returns 404."""
        fake_id = str(uuid.uuid4())
        clone_data = {"name": "Clone of Nothing", "version": "1.0.0"}

        response = client.post(
            f"v1/cms/flows/{fake_id}/clone",
            json=clone_data,
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestFlowNodes:
    """Test flow node management functionality."""

    def test_create_flow_node(self, client, backend_service_account_headers):
        """Test creating a node within a flow."""
        # Create flow first
        flow_data = {
            "name": "Flow with Nodes",
            "version": "1.0.0",
            "flow_data": {"entry_point": "start"},
            "entry_node_id": "start",
        }

        create_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = create_response.json()["id"]

        # Create a node
        node_data = {
            "node_id": "welcome_message",
            "node_type": "message",
            "template": "simple_message",
            "content": {
                "messages": [{"content_id": str(uuid.uuid4()), "delay": 1.5}],
                "typing_indicator": True,
            },
            "position": {"x": 100, "y": 50},
            "info": {"name": "Welcome Message", "description": "Greets the user"},
        }

        response = client.post(
            f"v1/cms/flows/{flow_id}/nodes",
            json=node_data,
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["node_id"] == "welcome_message"
        assert data["node_type"] == "message"
        assert data["template"] == "simple_message"
        assert data["position"]["x"] == 100
        assert data["content"]["typing_indicator"] is True

    def test_create_question_node(self, client, backend_service_account_headers):
        """Test creating a question node with options."""
        # Create flow first
        flow_data = {
            "name": "Flow with Question",
            "version": "1.0.0",
            "flow_data": {"entry_point": "start"},
            "entry_node_id": "start",
        }

        create_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = create_response.json()["id"]

        # Create question node
        node_data = {
            "node_id": "age_question",
            "node_type": "question",
            "template": "button_question",
            "content": {
                "question": {"content_id": str(uuid.uuid4())},
                "input_type": "buttons",
                "options": [
                    {"text": "Under 10", "value": "child", "payload": "$0"},
                    {"text": "10-17", "value": "teen", "payload": "$1"},
                    {"text": "18+", "value": "adult", "payload": "$2"},
                ],
                "validation": {"required": True, "type": "string"},
                "variable": "user_age_group",
            },
            "position": {"x": 200, "y": 100},
        }

        response = client.post(
            f"v1/cms/flows/{flow_id}/nodes",
            json=node_data,
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["node_type"] == "question"
        assert data["content"]["input_type"] == "buttons"
        assert len(data["content"]["options"]) == 3
        assert data["content"]["variable"] == "user_age_group"

    def test_list_flow_nodes(self, client, backend_service_account_headers):
        """Test listing all nodes in a flow."""
        # Create flow and add multiple nodes
        flow_data = {
            "name": "Multi-Node Flow",
            "version": "1.0.0",
            "flow_data": {"entry_point": "start"},
            "entry_node_id": "start",
        }

        create_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = create_response.json()["id"]

        # Create multiple nodes
        nodes = [
            {"node_id": "node1", "node_type": "message", "content": {"messages": []}},
            {"node_id": "node2", "node_type": "question", "content": {"question": {}}},
            {
                "node_id": "node3",
                "node_type": "condition",
                "content": {"conditions": []},
            },
        ]

        for node in nodes:
            client.post(
                f"v1/cms/flows/{flow_id}/nodes",
                json=node,
                headers=backend_service_account_headers,
            )

        # List all nodes
        response = client.get(
            f"v1/cms/flows/{flow_id}/nodes",
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]) == 3
        node_ids = [node["node_id"] for node in data["data"]]
        assert "node1" in node_ids
        assert "node2" in node_ids
        assert "node3" in node_ids

    def test_get_flow_node_by_id(self, client, backend_service_account_headers):
        """Test retrieving a specific node."""
        # Create flow and node
        flow_data = {
            "name": "Flow for Node Retrieval",
            "version": "1.0.0",
            "flow_data": {"entry_point": "start"},
            "entry_node_id": "start",
        }

        create_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = create_response.json()["id"]

        node_data = {
            "node_id": "test_node",
            "node_type": "message",
            "content": {"messages": [{"text": "Test message"}]},
        }

        node_response = client.post(
            f"v1/cms/flows/{flow_id}/nodes",
            json=node_data,
            headers=backend_service_account_headers,
        )
        node_db_id = node_response.json()["id"]

        # Get the node
        response = client.get(
            f"v1/cms/flows/{flow_id}/nodes/{node_db_id}",
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["node_id"] == "test_node"
        assert data["node_type"] == "message"

    def test_update_flow_node(self, client, backend_service_account_headers):
        """Test updating a flow node."""
        # Create flow and node
        flow_data = {
            "name": "Flow for Node Update",
            "version": "1.0.0",
            "flow_data": {"entry_point": "start"},
            "entry_node_id": "start",
        }

        create_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = create_response.json()["id"]

        node_data = {
            "node_id": "updatable_node",
            "node_type": "message",
            "content": {"messages": [{"text": "Original message"}]},
        }

        node_response = client.post(
            f"v1/cms/flows/{flow_id}/nodes",
            json=node_data,
            headers=backend_service_account_headers,
        )
        node_db_id = node_response.json()["id"]

        # Update the node
        update_data = {
            "content": {
                "messages": [{"text": "Updated message"}],
                "typing_indicator": True,
            },
            "position": {"x": 150, "y": 75},
            "info": {"updated": True},
        }

        response = client.put(
            f"v1/cms/flows/{flow_id}/nodes/{node_db_id}",
            json=update_data,
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["content"]["messages"][0]["text"] == "Updated message"
        assert data["content"]["typing_indicator"] is True
        assert data["position"]["x"] == 150

    def test_delete_flow_node(self, client, backend_service_account_headers):
        """Test deleting a flow node."""
        # Create flow and node
        flow_data = {
            "name": "Flow for Node Deletion",
            "version": "1.0.0",
            "flow_data": {"entry_point": "start"},
            "entry_node_id": "start",
        }

        create_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = create_response.json()["id"]

        node_data = {
            "node_id": "deletable_node",
            "node_type": "message",
            "content": {"messages": []},
        }

        node_response = client.post(
            f"v1/cms/flows/{flow_id}/nodes",
            json=node_data,
            headers=backend_service_account_headers,
        )
        node_db_id = node_response.json()["id"]

        # Delete the node
        response = client.delete(
            f"v1/cms/flows/{flow_id}/nodes/{node_db_id}",
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify node is deleted
        get_response = client.get(
            f"v1/cms/flows/{flow_id}/nodes/{node_db_id}",
            headers=backend_service_account_headers,
        )
        assert get_response.status_code == status.HTTP_404_NOT_FOUND


class TestFlowConnections:
    """Test flow connection management between nodes."""

    def test_create_flow_connection(self, client, backend_service_account_headers):
        """Test creating a connection between two nodes."""
        # Create flow and nodes first
        flow_data = {
            "name": "Flow with Connections",
            "version": "1.0.0",
            "flow_data": {"entry_point": "start"},
            "entry_node_id": "start",
        }

        create_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = create_response.json()["id"]

        # Create source and target nodes
        source_node = {
            "node_id": "source_node",
            "node_type": "question",
            "content": {"question": {}, "options": []},
        }

        target_node = {
            "node_id": "target_node",
            "node_type": "message",
            "content": {"messages": []},
        }

        source_response = client.post(
            f"v1/cms/flows/{flow_id}/nodes",
            json=source_node,
            headers=backend_service_account_headers,
        )
        source_node_id = source_response.json()["id"]

        target_response = client.post(
            f"v1/cms/flows/{flow_id}/nodes",
            json=target_node,
            headers=backend_service_account_headers,
        )
        target_node_id = target_response.json()["id"]

        # Create connection
        connection_data = {
            "source_node_id": source_node_id,
            "target_node_id": target_node_id,
            "connection_type": "default",
            "conditions": {"trigger": "user_response", "value": "yes"},
            "info": {"label": "Yes Branch", "priority": 1},
        }

        response = client.post(
            f"v1/cms/flows/{flow_id}/connections",
            json=connection_data,
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["source_node_id"] == source_node_id
        assert data["target_node_id"] == target_node_id
        assert data["connection_type"] == "default"
        assert data["conditions"]["value"] == "yes"

    def test_list_flow_connections(self, client, backend_service_account_headers):
        """Test listing all connections in a flow."""
        # Create flow with nodes and connections
        flow_data = {
            "name": "Multi-Connection Flow",
            "version": "1.0.0",
            "flow_data": {"entry_point": "start"},
            "entry_node_id": "start",
        }

        create_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = create_response.json()["id"]

        # Create nodes
        nodes = [
            {"node_id": "start", "node_type": "message", "content": {"messages": []}},
            {
                "node_id": "question",
                "node_type": "question",
                "content": {"question": {}},
            },
            {"node_id": "end", "node_type": "message", "content": {"messages": []}},
        ]

        node_ids = []
        for node in nodes:
            response = client.post(
                f"v1/cms/flows/{flow_id}/nodes",
                json=node,
                headers=backend_service_account_headers,
            )
            node_ids.append(response.json()["id"])

        # Create connections
        connections = [
            {
                "source_node_id": "start",
                "target_node_id": "question",
                "connection_type": "default",
            },
            {
                "source_node_id": "question",
                "target_node_id": "end",
                "connection_type": "default",
            },
        ]

        for connection in connections:
            client.post(
                f"v1/cms/flows/{flow_id}/connections",
                json=connection,
                headers=backend_service_account_headers,
            )

        # List all connections
        response = client.get(
            f"v1/cms/flows/{flow_id}/connections",
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]) == 2

    def test_delete_flow_connection(self, client, backend_service_account_headers):
        """Test deleting a flow connection."""
        # Create flow, nodes, and connection
        flow_data = {
            "name": "Flow for Connection Deletion",
            "version": "1.0.0",
            "flow_data": {"entry_point": "start"},
            "entry_node_id": "start",
        }

        create_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = create_response.json()["id"]

        # Create two nodes
        node1 = client.post(
            f"v1/cms/flows/{flow_id}/nodes",
            json={
                "node_id": "node1",
                "node_type": "message",
                "content": {"messages": []},
            },
            headers=backend_service_account_headers,
        ).json()["id"]

        node2 = client.post(
            f"v1/cms/flows/{flow_id}/nodes",
            json={
                "node_id": "node2",
                "node_type": "message",
                "content": {"messages": []},
            },
            headers=backend_service_account_headers,
        ).json()["id"]

        # Create connection
        connection_data = {
            "source_node_id": node1,
            "target_node_id": node2,
            "connection_type": "default",
        }

        connection_response = client.post(
            f"v1/cms/flows/{flow_id}/connections",
            json=connection_data,
            headers=backend_service_account_headers,
        )
        connection_id = connection_response.json()["id"]

        # Delete the connection
        response = client.delete(
            f"v1/cms/flows/{flow_id}/connections/{connection_id}",
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify connection is deleted
        list_response = client.get(
            f"v1/cms/flows/{flow_id}/connections",
            headers=backend_service_account_headers,
        )
        connection_ids = [c["id"] for c in list_response.json()["data"]]
        assert connection_id not in connection_ids


class TestFlowValidation:
    """Test flow validation and integrity checks."""

    def test_validate_flow_structure(self, client, backend_service_account_headers):
        """Test validating flow structure and integrity."""
        # Create flow with nodes and connections
        flow_data = {
            "name": "Flow for Validation",
            "version": "1.0.0",
            "flow_data": {"entry_point": "start"},
            "entry_node_id": "start",
        }

        create_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = create_response.json()["id"]

        # Validate flow structure
        response = client.get(
            f"v1/cms/flows/{flow_id}/validate",
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "is_valid" in data
        assert "validation_errors" in data
        assert "validation_warnings" in data

    def test_flow_with_missing_entry_node_validation(
        self, client, backend_service_account_headers
    ):
        """Test validation fails when entry node is missing."""
        # Create flow with invalid entry node
        flow_data = {
            "name": "Invalid Flow",
            "version": "1.0.0",
            "flow_data": {"entry_point": "missing_node"},
            "entry_node_id": "missing_node",
        }

        create_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        flow_id = create_response.json()["id"]

        # Validate should fail
        response = client.get(
            f"v1/cms/flows/{flow_id}/validate",
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_valid"] is False
        assert len(data["validation_errors"]) > 0

    def test_flow_with_invalid_variable_syntax_warns(
        self, client, backend_service_account_headers
    ):
        """Test validation warns about variables without scope prefix."""
        # Create flow with invalid variable syntax (missing scope prefix)
        flow_data = {
            "name": "Flow With Invalid Variables",
            "version": "1.0.0",
            "entry_node_id": "start",
            "flow_data": {
                "nodes": [
                    {
                        "id": "start",
                        "type": "START",
                        "position": {"x": 0, "y": 0},
                        "content": {},
                    },
                    {
                        "id": "message1",
                        "type": "MESSAGE",
                        "position": {"x": 0, "y": 100},
                        "content": {
                            # Invalid: missing scope prefix
                            "text": "Hello {{ name }}, your color is {{ favorite_color }}!"
                        },
                    },
                ],
                "connections": [
                    {"source": "start", "target": "message1", "type": "DEFAULT"}
                ],
            },
        }

        create_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        flow_id = create_response.json()["id"]

        # Validate should return warnings about variable syntax
        response = client.get(
            f"v1/cms/flows/{flow_id}/validate",
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Flow is still valid but has warnings
        assert data["is_valid"] is True
        # Should have warnings about missing scope prefix
        assert len(data["validation_warnings"]) >= 2
        # Check that warnings mention the variables
        warnings_text = " ".join(data["validation_warnings"])
        assert "name" in warnings_text
        assert "favorite_color" in warnings_text
        assert "temp." in warnings_text  # Should suggest correct syntax

    def test_flow_with_valid_variable_syntax_no_warnings(
        self, client, backend_service_account_headers
    ):
        """Test validation passes with correct variable syntax."""
        # Create flow with valid variable syntax (proper scope prefix)
        flow_data = {
            "name": "Flow With Valid Variables",
            "version": "1.0.0",
            "entry_node_id": "start",
            "flow_data": {
                "nodes": [
                    {
                        "id": "start",
                        "type": "START",
                        "position": {"x": 0, "y": 0},
                        "content": {},
                    },
                    {
                        "id": "message1",
                        "type": "MESSAGE",
                        "position": {"x": 0, "y": 100},
                        "content": {
                            # Valid: uses temp. scope prefix
                            "text": "Hello {{ temp.name }}, your color is {{ temp.favorite_color }}!"
                        },
                    },
                ],
                "connections": [
                    {"source": "start", "target": "message1", "type": "DEFAULT"}
                ],
            },
        }

        create_response = client.post(
            "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        flow_id = create_response.json()["id"]

        # Validate should pass without variable warnings
        response = client.get(
            f"v1/cms/flows/{flow_id}/validate",
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_valid"] is True
        # No variable-related warnings (might have other warnings like orphaned nodes)
        var_warnings = [w for w in data["validation_warnings"] if "Variable" in w]
        assert len(var_warnings) == 0


class TestFlowAuthentication:
    """Test flow operations require proper authentication."""

    def test_list_flows_requires_authentication(self, client):
        """Test that listing flows requires authentication."""
        response = client.get("v1/cms/flows")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_flow_requires_authentication(self, client):
        """Test that creating flows requires authentication."""
        flow_data = {"name": "Test Flow", "version": "1.0.0"}
        response = client.post("v1/cms/flows", json=flow_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_flow_requires_authentication(self, client):
        """Test that updating flows requires authentication."""
        fake_id = str(uuid.uuid4())
        update_data = {"name": "Updated Flow"}
        response = client.put(f"v1/cms/flows/{fake_id}", json=update_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_flow_requires_authentication(self, client):
        """Test that deleting flows requires authentication."""
        fake_id = str(uuid.uuid4())
        response = client.delete(f"v1/cms/flows/{fake_id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_publish_flow_requires_authentication(self, client):
        """Test that publishing flows requires authentication."""
        fake_id = str(uuid.uuid4())
        response = client.post(f"v1/cms/flows/{fake_id}/publish")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_clone_flow_requires_authentication(self, client):
        """Test that cloning flows requires authentication."""
        fake_id = str(uuid.uuid4())
        clone_data = {"name": "Cloned Flow"}
        response = client.post(f"v1/cms/flows/{fake_id}/clone", json=clone_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
