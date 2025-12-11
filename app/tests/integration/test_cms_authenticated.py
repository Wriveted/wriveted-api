"""
Integration tests for CMS and Chat APIs with proper authentication.
Tests the authenticated CMS routes and chat functionality.
"""

from uuid import uuid4

import pytest
from sqlalchemy import text


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


class TestCMSWithAuthentication:
    """Test CMS functionality with proper authentication."""

    def test_cms_content_requires_authentication(self, client):
        """Test that CMS content endpoints require authentication."""
        # Try to access CMS content without auth
        response = client.get("/v1/cms/content")
        assert response.status_code == 401

        # Try to create content without auth
        response = client.post("/v1/cms/content", json={"type": "joke"})
        assert response.status_code == 401

    def test_cms_flows_require_authentication(self, client):
        """Test that CMS flow endpoints require authentication."""
        # Try to access flows without auth
        response = client.get("/v1/cms/flows")
        assert response.status_code == 401

        # Try to create flow without auth
        response = client.post("/v1/cms/flows", json={"name": "Test"})
        assert response.status_code == 401

    def test_chat_start_does_not_require_auth(self, client):
        """Test that chat start endpoint does not require authentication."""
        # This should fail for other reasons (invalid flow), but not auth
        response = client.post(
            "/v1/chat/start",
            json={"flow_id": str(uuid4()), "user_id": None, "initial_state": {}},
        )

        # Should not be 401 (auth error), but 404 (flow not found)
        assert response.status_code != 401
        assert response.status_code == 404

    def test_create_cms_content_with_auth(
        self, client, backend_service_account_headers
    ):
        """Test creating CMS content with proper authentication."""
        joke_data = {
            "type": "joke",
            "content": {
                "text": "Why do programmers prefer dark mode? Because light attracts bugs!",
                "category": "programming",
                "audience": "developers",
            },
            "status": "PUBLISHED",
            "tags": ["programming", "humor", "developers"],
            "info": {"source": "pytest_test", "difficulty": "easy", "rating": 4.2},
        }

        response = client.post(
            "/v1/cms/content", json=joke_data, headers=backend_service_account_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "joke"
        assert data["status"] == "published"
        assert "programming" in data["tags"]
        assert data["info"]["source"] == "pytest_test"
        assert "id" in data

    def test_list_cms_content_with_auth(self, client, backend_service_account_headers):
        """Test listing CMS content with authentication."""
        # First create some content directly (not by calling another test)
        joke_data = {
            "type": "joke",
            "content": {
                "text": "Why did the test fail? Because it called another test!",
                "category": "testing",
                "audience": "developers",
            },
            "status": "PUBLISHED",
            "tags": ["testing", "humor"],
            "info": {"source": "test_list", "difficulty": "easy"},
        }

        create_response = client.post(
            "/v1/cms/content", json=joke_data, headers=backend_service_account_headers
        )
        assert create_response.status_code == 201
        created_content = create_response.json()
        content_id = created_content["id"]

        # Now list the content
        response = client.get(
            "/v1/cms/content", headers=backend_service_account_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) >= 1

        # Verify our created content is in the list
        content_ids = [item["id"] for item in data["data"]]
        assert content_id in content_ids

    def test_filter_cms_content_by_type(self, client, backend_service_account_headers):
        """Test filtering CMS content by type."""
        # Create a joke directly (not by calling another test)
        joke_data = {
            "type": "joke",
            "content": {
                "text": "Why do tests hate dependencies? They prefer isolation!",
                "category": "testing",
                "audience": "developers",
            },
            "status": "PUBLISHED",
            "tags": ["filter", "test"],
            "info": {"source": "test_filter", "difficulty": "medium"},
        }

        create_response = client.post(
            "/v1/cms/content", json=joke_data, headers=backend_service_account_headers
        )
        assert create_response.status_code == 201
        created_joke = create_response.json()
        joke_id = created_joke["id"]

        # Filter by JOKE type
        response = client.get(
            "/v1/cms/content?content_type=JOKE", headers=backend_service_account_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) >= 1

        # All returned items should be jokes
        for item in data["data"]:
            assert item["type"] == "joke"

        # Verify our created joke is in the filtered results
        joke_ids = [item["id"] for item in data["data"]]
        assert joke_id in joke_ids

    def test_create_flow_definition_with_auth(
        self, client, backend_service_account_headers
    ):
        """Test creating a flow definition with authentication."""
        flow_data = {
            "name": "Test Programming Assessment",
            "description": "A simple programming assessment flow",
            "version": "1.0",
            "flow_data": {
                "nodes": [
                    {
                        "id": "welcome",
                        "type": "message",
                        "content": {"text": "Welcome to our programming assessment!"},
                        "position": {"x": 100, "y": 100},
                    },
                    {
                        "id": "ask_experience",
                        "type": "question",
                        "content": {
                            "text": "How many years of programming experience do you have?",
                            "options": ["0-1 years", "2-5 years", "5+ years"],
                            "variable": "experience",
                        },
                        "position": {"x": 100, "y": 200},
                    },
                ],
                "connections": [
                    {"source": "welcome", "target": "ask_experience", "type": "DEFAULT"}
                ],
            },
            "entry_node_id": "welcome",
            "info": {"author": "pytest", "category": "assessment"},
        }

        response = client.post(
            "/v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Programming Assessment"
        assert data["is_published"] is False
        assert data["is_active"] is True
        assert len(data["flow_data"]["nodes"]) == 2
        assert len(data["flow_data"]["connections"]) == 1

    def test_list_flows_with_auth(self, client, backend_service_account_headers):
        """Test listing flows with authentication."""
        # Create a flow directly (not by calling another test)
        flow_data = {
            "name": "Test Flow for Listing",
            "description": "A flow created for list testing",
            "version": "1.0",
            "flow_data": {
                "nodes": [
                    {
                        "id": "start",
                        "type": "message",
                        "content": {"text": "Testing flow listing"},
                        "position": {"x": 100, "y": 100},
                    }
                ],
            },
            "entry_node_id": "start",
            "info": {"purpose": "list_test"},
        }

        create_response = client.post(
            "/v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        assert create_response.status_code == 201
        created_flow = create_response.json()
        flow_id = created_flow["id"]

        # Now list the flows
        response = client.get("/v1/cms/flows", headers=backend_service_account_headers)

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) >= 1

        # Verify our created flow is in the list
        flow_ids = [f["id"] for f in data["data"]]
        assert flow_id in flow_ids

    def test_get_flow_nodes_with_auth(self, client, backend_service_account_headers):
        """Test getting flow nodes with authentication."""
        # Create a flow first
        flow_data = {
            "name": "Test Node Flow",
            "description": "A flow for testing nodes",
            "version": "1.0",
            "flow_data": {
                "nodes": [
                    {
                        "id": "welcome",
                        "type": "message",
                        "content": {"text": "Welcome!"},
                        "position": {"x": 100, "y": 100},
                    },
                    {
                        "id": "ask_question",
                        "type": "question",
                        "content": {
                            "text": "What's your name?",
                            "variable": "user_name",
                        },
                        "position": {"x": 100, "y": 200},
                    },
                ],
                "connections": [
                    {"source": "welcome", "target": "ask_question", "type": "DEFAULT"}
                ],
            },
            "entry_node_id": "welcome",
            "info": {"test": "node_test"},
        }

        flow_response = client.post(
            "/v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        assert flow_response.status_code == 201
        flow_id = flow_response.json()["id"]

        response = client.get(
            f"/v1/cms/flows/{flow_id}/nodes", headers=backend_service_account_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) == 2

        # Check node types
        node_types = {node["node_type"] for node in data["data"]}
        assert "message" in node_types
        assert "question" in node_types

    def test_start_chat_session_with_created_flow(
        self, client, backend_service_account_headers
    ):
        """Test starting a chat session with a flow we created."""
        # Create a flow directly (not by calling another test)
        flow_data = {
            "name": "Test Flow for Chat Session",
            "description": "A flow created for chat session testing",
            "version": "1.0",
            "flow_data": {
                "nodes": [
                    {
                        "id": "welcome",
                        "type": "message",
                        "content": {"text": "Welcome to the test chat!"},
                        "position": {"x": 100, "y": 100},
                    },
                    {
                        "id": "question",
                        "type": "question",
                        "content": {
                            "text": "How are you?",
                            "options": ["Good", "Great"],
                            "variable": "mood",
                        },
                        "position": {"x": 100, "y": 200},
                    },
                ],
                "connections": [
                    {"source": "welcome", "target": "question", "type": "DEFAULT"}
                ],
            },
            "entry_node_id": "welcome",
            "info": {"purpose": "chat_test"},
        }

        create_response = client.post(
            "/v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        assert create_response.status_code == 201
        flow_id = create_response.json()["id"]

        # Publish the flow so it can be used for chat
        publish_response = client.post(
            f"/v1/cms/flows/{flow_id}/publish",
            json={"publish": True},
            headers=backend_service_account_headers,
        )
        assert publish_response.status_code == 200

        session_data = {
            "flow_id": flow_id,
            "user_id": None,
            "initial_state": {"test_mode": True, "source": "pytest"},
        }

        response = client.post("/v1/chat/start", json=session_data)

        assert response.status_code == 201
        data = response.json()
        assert "session_id" in data
        assert "session_token" in data
        assert data["session_id"] is not None
        assert data["session_token"] is not None

        # Test getting session state
        session_token = data["session_token"]
        response = client.get(f"/v1/chat/sessions/{session_token}")

        assert response.status_code == 200
        session_data = response.json()
        assert session_data["status"] == "active"
        assert "state" in session_data
        assert session_data["state"]["test_mode"] is True
        assert session_data["state"]["source"] == "pytest"

    def test_complete_cms_to_chat_workflow(
        self, client, backend_service_account_headers
    ):
        """Test complete workflow from CMS content creation to chat session."""
        print("\\n🧪 Testing complete CMS to Chat workflow...")

        # 1. Create CMS content directly
        print("   📝 Creating CMS content...")
        content_data = {
            "type": "joke",
            "content": {
                "text": "Complete workflow test joke!",
                "category": "workflow",
            },
            "status": "PUBLISHED",
            "tags": ["workflow", "test"],
            "info": {"source": "workflow_test"},
        }

        content_response = client.post(
            "/v1/cms/content",
            json=content_data,
            headers=backend_service_account_headers,
        )
        assert content_response.status_code == 201
        content_id = content_response.json()["id"]
        print(f"   ✅ Created content: {content_id}")

        # 2. Create a flow directly
        print("   🔗 Creating flow definition...")
        flow_data = {
            "name": "Complete Workflow Test Flow",
            "description": "End-to-end workflow test",
            "version": "1.0",
            "flow_data": {
                "nodes": [
                    {
                        "id": "start",
                        "type": "message",
                        "content": {"text": "Workflow test!"},
                        "position": {"x": 100, "y": 100},
                    }
                ],
            },
            "entry_node_id": "start",
            "info": {"workflow": "complete_test"},
        }

        flow_response = client.post(
            "/v1/cms/flows", json=flow_data, headers=backend_service_account_headers
        )
        assert flow_response.status_code == 201
        flow_id = flow_response.json()["id"]
        print(f"   ✅ Created flow: {flow_id}")

        # 3. Verify content is accessible
        print("   📋 Verifying content accessibility...")
        content_response = client.get(
            "/v1/cms/content", headers=backend_service_account_headers
        )
        assert content_response.status_code == 200
        content_data = content_response.json()

        retrieved_ids = {item["id"] for item in content_data["data"]}
        assert content_id in retrieved_ids
        print(f"   ✅ Content accessible: {len(content_data['data'])} items total")

        # 4. Start a chat session with the created flow
        print("   💬 Starting chat session...")
        # First publish the flow
        publish_response = client.post(
            f"/v1/cms/flows/{flow_id}/publish",
            json={"publish": True},
            headers=backend_service_account_headers,
        )
        assert publish_response.status_code == 200

        # Now start the session
        session_data = {
            "flow_id": flow_id,
            "user_id": None,
            "initial_state": {"test_mode": True, "source": "workflow_test"},
        }

        session_response = client.post("/v1/chat/start", json=session_data)
        assert session_response.status_code == 201
        session_info = session_response.json()
        session_token = session_info["session_token"]
        print(f"   ✅ Started session: {session_token[:20]}...")

        # 5. Verify flows are accessible
        print("   🔍 Verifying flow accessibility...")
        flows_response = client.get(
            "/v1/cms/flows", headers=backend_service_account_headers
        )
        assert flows_response.status_code == 200
        flows_data = flows_response.json()

        flow_ids = {flow["id"] for flow in flows_data["data"]}
        assert flow_id in flow_ids
        print(f"   ✅ Flow accessible: {len(flows_data['data'])} flows total")

        print("\\n🎉 Complete workflow test passed!")
        print("   📊 Summary:")
        print("   - CMS Content created and accessible ✅")
        print("   - Flow definition created and accessible ✅")
        print("   - Chat session started successfully ✅")
        print("   - Authentication working properly ✅")
        print("   - End-to-end workflow verified ✅")
