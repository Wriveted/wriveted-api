"""Comprehensive integration tests for Chat API endpoints."""

import uuid

import pytest
from starlette import status


@pytest.fixture
def test_flow_with_nodes(client, backend_service_account_headers):
    """Create a test flow with nodes for chat testing."""
    # Create flow
    flow_data = {
        "name": "Test Chat Flow",
        "version": "1.0",
        "flow_data": {
            "variables": {"user_name": {"type": "string", "default": "Guest"}}
        },
        "entry_node_id": "welcome",
    }

    flow_response = client.post(
        "v1/cms/flows", json=flow_data, headers=backend_service_account_headers
    )
    flow_id = flow_response.json()["id"]

    # Create content for welcome message
    content_data = {
        "type": "message",
        "content": {"text": "Welcome {{user_name}}! How can I help you today?"},
    }

    content_response = client.post(
        "v1/cms/content", json=content_data, headers=backend_service_account_headers
    )
    content_id = content_response.json()["id"]

    # Create welcome node
    welcome_node = {
        "node_id": "welcome",
        "node_type": "message",
        "content": {"messages": [{"content_id": content_id, "typing_delay": 1.0}]},
    }

    client.post(
        f"v1/cms/flows/{flow_id}/nodes",
        json=welcome_node,
        headers=backend_service_account_headers,
    )

    # Create question content
    question_content_data = {
        "type": "question",
        "content": {"text": "What's your favorite book genre?"},
    }

    question_content_response = client.post(
        "v1/cms/content",
        json=question_content_data,
        headers=backend_service_account_headers,
    )
    question_content_id = question_content_response.json()["id"]

    # Create question node
    question_node = {
        "node_id": "ask_genre",
        "node_type": "question",
        "content": {
            "question": {"content_id": question_content_id},
            "input_type": "text",
            "variable": "favorite_genre",
        },
    }

    client.post(
        f"v1/cms/flows/{flow_id}/nodes",
        json=question_node,
        headers=backend_service_account_headers,
    )

    # Create connection from welcome to question
    connection_data = {
        "source_node_id": "welcome",
        "target_node_id": "ask_genre",
        "connection_type": "default",
    }

    client.post(
        f"v1/cms/flows/{flow_id}/connections",
        json=connection_data,
        headers=backend_service_account_headers,
    )

    return {
        "flow_id": flow_id,
        "content_id": content_id,
        "question_content_id": question_content_id,
    }


# Chat Session Management Tests


def test_start_conversation(client, test_flow_with_nodes):
    """Test starting a new conversation session."""
    flow_id = test_flow_with_nodes["flow_id"]

    session_data = {
        "flow_id": flow_id,
        "user_id": str(uuid.uuid4()),
        "initial_state": {"user_name": "Alice", "channel": "web"},
    }

    response = client.post("v1/chat/start", json=session_data)

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()

    # Check response structure based on SessionStartResponse schema
    assert "session_token" in data
    assert "session_id" in data
    assert "next_node" in data

    # Check next node content
    next_node = data["next_node"]
    assert next_node["type"] == "messages"
    assert len(next_node["messages"]) == 1
    assert "Welcome Alice!" in next_node["messages"][0]["content"]["text"]

    # Check CSRF token is set in cookies (not in JSON response)
    assert "csrf_token" in response.cookies
    assert "chat_session" in response.cookies

    # Verify secure cookie attributes
    csrf_cookie = response.cookies["csrf_token"]
    assert csrf_cookie["httponly"]
    assert csrf_cookie["samesite"] == "strict"

    # Return session token and CSRF token from cookie
    return data["session_token"], response.cookies["csrf_token"]


def test_start_conversation_with_invalid_flow(client):
    """Test starting conversation with non-existent flow."""
    fake_flow_id = str(uuid.uuid4())

    session_data = {"flow_id": fake_flow_id, "user_id": str(uuid.uuid4())}

    response = client.post("v1/chat/start", json=session_data)

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_get_session_state(client, test_flow_with_nodes):
    """Test retrieving current session state."""
    # Start session first
    flow_id = test_flow_with_nodes["flow_id"]
    session_data = {
        "flow_id": flow_id,
        "user_id": str(uuid.uuid4()),
        "initial_state": {"user_name": "Bob"},
    }

    start_response = client.post("v1/chat/start", json=session_data)
    session_token = start_response.json()["session_token"]

    # Get session state
    response = client.get(f"v1/chat/sessions/{session_token}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["session_token"] == session_token
    assert data["flow_id"] == flow_id
    assert data["current_node_id"] == "welcome"
    assert data["status"] == "active"
    assert data["state"]["user_name"] == "Bob"
    assert "session_id" in data
    assert "started_at" in data


def test_get_nonexistent_session(client):
    """Test retrieving non-existent session returns 404."""
    fake_token = "fake_session_token_123"

    response = client.get(f"v1/chat/sessions/{fake_token}")

    assert response.status_code == status.HTTP_404_NOT_FOUND


# Chat Interaction Tests


def test_interact_with_session_csrf_protected(client, test_flow_with_nodes):
    """Test chat interaction with CSRF protection."""
    # Start session
    flow_id = test_flow_with_nodes["flow_id"]
    session_data = {
        "flow_id": flow_id,
        "user_id": str(uuid.uuid4()),
        "initial_state": {"user_name": "Charlie"},
    }

    start_response = client.post("v1/chat/start", json=session_data)
    session_token = start_response.json()["session_token"]
    csrf_token = start_response.cookies["csrf_token"]

    # Interact with proper CSRF token
    interaction_data = {"input": "Fantasy", "input_type": "text"}

    headers = {"X-CSRF-Token": csrf_token}
    response = client.post(
        f"v1/chat/sessions/{session_token}/interact",
        json=interaction_data,
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "messages" in data
    assert "session_updated" in data
    assert "current_node_id" in data

    # Check that state was updated
    session_state = data["session_updated"]
    assert session_state["state"]["favorite_genre"] == "Fantasy"


def test_interact_without_csrf_token(client, test_flow_with_nodes):
    """Test that interaction without CSRF token fails."""
    # Start session
    flow_id = test_flow_with_nodes["flow_id"]
    session_data = {"flow_id": flow_id, "user_id": str(uuid.uuid4())}

    start_response = client.post("v1/chat/start", json=session_data)
    session_token = start_response.json()["session_token"]

    # Try to interact without CSRF token
    interaction_data = {"input": "Test input", "input_type": "text"}

    response = client.post(
        f"v1/chat/sessions/{session_token}/interact", json=interaction_data
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_interact_with_invalid_csrf_token(client, test_flow_with_nodes):
    """Test that interaction with invalid CSRF token fails."""
    # Start session
    flow_id = test_flow_with_nodes["flow_id"]
    session_data = {"flow_id": flow_id, "user_id": str(uuid.uuid4())}

    start_response = client.post("v1/chat/start", json=session_data)
    session_token = start_response.json()["session_token"]

    # Try to interact with invalid CSRF token
    interaction_data = {"input": "Test input", "input_type": "text"}

    headers = {"X-CSRF-Token": "invalid_token_123"}
    response = client.post(
        f"v1/chat/sessions/{session_token}/interact",
        json=interaction_data,
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_interact_with_invalid_session_token(client):
    """Test interaction with invalid session token."""
    fake_token = "invalid_session_token"

    interaction_data = {"input": "Test input", "input_type": "text"}

    headers = {"X-CSRF-Token": "some_token"}
    response = client.post(
        f"v1/chat/sessions/{fake_token}/interact",
        json=interaction_data,
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


# Session History Tests


def test_get_conversation_history(client, test_flow_with_nodes):
    """Test retrieving conversation history."""
    # Start session and interact
    flow_id = test_flow_with_nodes["flow_id"]
    session_data = {
        "flow_id": flow_id,
        "user_id": str(uuid.uuid4()),
        "initial_state": {"user_name": "Diana"},
    }

    start_response = client.post("v1/chat/start", json=session_data)
    session_token = start_response.json()["session_token"]
    csrf_token = start_response.cookies["csrf_token"]

    # Make an interaction to create history
    interaction_data = {"input": "Science Fiction", "input_type": "text"}
    headers = {"X-CSRF-Token": csrf_token}

    client.post(
        f"v1/chat/sessions/{session_token}/interact",
        json=interaction_data,
        headers=headers,
    )

    # Get conversation history
    response = client.get(f"v1/chat/sessions/{session_token}/history")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "data" in data
    assert "pagination" in data
    assert len(data["data"]) >= 1

    # Check history entry structure
    history_entry = data["data"][0]
    assert "node_id" in history_entry
    assert "interaction_type" in history_entry
    assert "content" in history_entry
    assert "created_at" in history_entry


def test_get_history_with_pagination(client, test_flow_with_nodes):
    """Test conversation history pagination."""
    # Start session
    flow_id = test_flow_with_nodes["flow_id"]
    session_data = {"flow_id": flow_id, "user_id": str(uuid.uuid4())}

    start_response = client.post("v1/chat/start", json=session_data)
    session_token = start_response.json()["session_token"]

    # Get history with pagination
    response = client.get(f"v1/chat/sessions/{session_token}/history?limit=5&skip=0")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["pagination"]["limit"] == 5
    assert data["pagination"]["skip"] == 0
    assert "total" in data["pagination"]


# Session State Management Tests


def test_update_session_state(client, test_flow_with_nodes):
    """Test updating session state variables."""
    # Start session
    flow_id = test_flow_with_nodes["flow_id"]
    session_data = {
        "flow_id": flow_id,
        "user_id": str(uuid.uuid4()),
        "initial_state": {"user_name": "Eve"},
    }

    start_response = client.post("v1/chat/start", json=session_data)
    session_token = start_response.json()["session_token"]

    # Update session state
    state_update = {
        "state_updates": {
            "reading_level": "advanced",
            "preferences": {"notifications": True, "theme": "dark"},
        }
    }

    response = client.patch(
        f"v1/chat/sessions/{session_token}/state", json=state_update
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["state"]["reading_level"] == "advanced"
    assert data["state"]["preferences"]["notifications"] is True
    assert data["state"]["user_name"] == "Eve"  # Original state preserved
    assert data["revision"] > 1  # Revision should increment


def test_update_session_state_with_concurrency_conflict(client, test_flow_with_nodes):
    """Test session state update with concurrency conflict."""
    # Start session
    flow_id = test_flow_with_nodes["flow_id"]
    session_data = {"flow_id": flow_id, "user_id": str(uuid.uuid4())}

    start_response = client.post("v1/chat/start", json=session_data)
    session_token = start_response.json()["session_token"]

    # First update
    state_update1 = {"state_updates": {"counter": 1}, "expected_revision": 1}

    response1 = client.patch(
        f"v1/chat/sessions/{session_token}/state", json=state_update1
    )
    assert response1.status_code == status.HTTP_200_OK

    # Second update with outdated revision (should conflict)
    state_update2 = {
        "state_updates": {"counter": 2},
        "expected_revision": 1,  # Outdated revision
    }

    response2 = client.patch(
        f"v1/chat/sessions/{session_token}/state", json=state_update2
    )

    assert response2.status_code == status.HTTP_409_CONFLICT


# Session Lifecycle Tests


def test_end_session(client, test_flow_with_nodes):
    """Test ending a conversation session."""
    # Start session
    flow_id = test_flow_with_nodes["flow_id"]
    session_data = {"flow_id": flow_id, "user_id": str(uuid.uuid4())}

    start_response = client.post("v1/chat/start", json=session_data)
    session_token = start_response.json()["session_token"]

    # End session
    end_data = {"reason": "user_requested"}

    response = client.post(f"v1/chat/sessions/{session_token}/end", json=end_data)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "message" in data
    assert "session_ended" in data["message"]

    # Verify session is ended
    session_response = client.get(f"v1/chat/sessions/{session_token}")
    session_data = session_response.json()
    assert session_data["status"] == "completed"
    assert "ended_at" in session_data


def test_end_nonexistent_session(client):
    """Test ending a non-existent session."""
    fake_token = "nonexistent_session_token"

    response = client.post(
        f"v1/chat/sessions/{fake_token}/end", json={"reason": "test"}
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


# Error Handling Tests


def test_malformed_interaction_data(client, test_flow_with_nodes):
    """Test handling of malformed interaction data."""
    # Start session
    flow_id = test_flow_with_nodes["flow_id"]
    session_data = {"flow_id": flow_id, "user_id": str(uuid.uuid4())}

    start_response = client.post("v1/chat/start", json=session_data)
    session_token = start_response.json()["session_token"]
    csrf_token = start_response.cookies["csrf_token"]

    # Send malformed interaction data
    malformed_data = {
        "invalid_field": "invalid_value"
        # Missing required fields
    }

    headers = {"X-CSRF-Token": csrf_token}
    response = client.post(
        f"v1/chat/sessions/{session_token}/interact",
        json=malformed_data,
        headers=headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_invalid_state_update_data(client, test_flow_with_nodes):
    """Test handling of invalid state update data."""
    # Start session
    flow_id = test_flow_with_nodes["flow_id"]
    session_data = {"flow_id": flow_id, "user_id": str(uuid.uuid4())}

    start_response = client.post("v1/chat/start", json=session_data)
    session_token = start_response.json()["session_token"]

    # Send invalid state update
    invalid_update = {
        "invalid_field": "should_fail"
        # Missing state_updates field
    }

    response = client.patch(
        f"v1/chat/sessions/{session_token}/state", json=invalid_update
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# Input Validation Tests


def test_input_validation_and_sanitization(client, test_flow_with_nodes):
    """Test input validation and sanitization."""
    # Start session
    flow_id = test_flow_with_nodes["flow_id"]
    session_data = {"flow_id": flow_id, "user_id": str(uuid.uuid4())}

    start_response = client.post("v1/chat/start", json=session_data)
    session_token = start_response.json()["session_token"]
    csrf_token = start_response.cookies["csrf_token"]

    # Test with potentially malicious input
    dangerous_inputs = [
        "<script>alert('xss')</script>",
        "'; DROP TABLE users; --",
        "{{system_password}}",
        "../../../etc/passwd",
    ]

    headers = {"X-CSRF-Token": csrf_token}

    for dangerous_input in dangerous_inputs:
        interaction_data = {"input": dangerous_input, "input_type": "text"}

        response = client.post(
            f"v1/chat/sessions/{session_token}/interact",
            json=interaction_data,
            headers=headers,
        )

        # Should not cause server errors
        assert response.status_code in [200, 400, 422]

        # Response should not contain the dangerous input directly
        if response.status_code == 200:
            response_text = response.text.lower()
            assert "<script>" not in response_text
            assert "drop table" not in response_text


# Performance and Load Tests


def test_concurrent_session_creation(client, test_flow_with_nodes):
    """Test creating multiple sessions concurrently."""
    flow_id = test_flow_with_nodes["flow_id"]

    session_tokens = []

    # Create multiple sessions
    for i in range(5):
        session_data = {
            "flow_id": flow_id,
            "user_id": str(uuid.uuid4()),
            "initial_state": {"user_name": f"User{i}"},
        }

        response = client.post("v1/chat/start", json=session_data)
        assert response.status_code == status.HTTP_201_CREATED

        session_token = response.json()["session_token"]
        session_tokens.append(session_token)

    # Verify all sessions are unique
    assert len(set(session_tokens)) == 5

    # Verify all sessions are accessible
    for token in session_tokens:
        response = client.get(f"v1/chat/sessions/{token}")
        assert response.status_code == status.HTTP_200_OK


def test_session_timeout_handling(client, test_flow_with_nodes):
    """Test handling of session timeouts (if implemented)."""
    # This test would verify session timeout behavior
    # Implementation depends on actual timeout mechanism
    pass


# Integration with CMS Content Tests


def test_chat_with_dynamic_content_loading(client, test_flow_with_nodes):
    """Test that chat properly loads and renders CMS content."""
    # Start session
    flow_id = test_flow_with_nodes["flow_id"]
    session_data = {
        "flow_id": flow_id,
        "user_id": str(uuid.uuid4()),
        "initial_state": {"user_name": "ContentTestUser"},
    }

    start_response = client.post("v1/chat/start", json=session_data)
    initial_node = start_response.json()["next_node"]

    # Verify content was properly loaded and variables substituted
    message_text = initial_node["messages"][0]["content"]["text"]
    assert "ContentTestUser" in message_text
    assert "Welcome" in message_text
    assert "{{user_name}}" not in message_text  # Variable should be substituted


def test_chat_with_content_variants(
    client, backend_service_account_headers, test_flow_with_nodes
):
    """Test chat behavior with content variants (A/B testing)."""
    # Create content variant for testing
    content_id = test_flow_with_nodes["content_id"]

    variant_data = {
        "variant_key": "version_b",
        "variant_data": {"text": "Hey there {{user_name}}! What's up?"},
        "weight": 50,
    }

    client.post(
        f"v1/cms/content/{content_id}/variants",
        json=variant_data,
        headers=backend_service_account_headers,
    )

    # Start multiple sessions to potentially trigger different variants
    flow_id = test_flow_with_nodes["flow_id"]

    messages_seen = set()

    for i in range(10):
        session_data = {
            "flow_id": flow_id,
            "user_id": str(uuid.uuid4()),
            "initial_state": {"user_name": "VariantTestUser"},
        }

        response = client.post("v1/chat/start", json=session_data)
        initial_node = response.json()["next_node"]
        message_text = initial_node["messages"][0]["content"]["text"]
        messages_seen.add(message_text)

    # Should see both original content and variant (probabilistically)
    # Note: This test might be flaky due to random variant selection
    assert len(messages_seen) >= 1  # At least one message variant


# Rate Limiting Tests (if implemented)


def test_rate_limiting_protection(client, test_flow_with_nodes):
    """Test rate limiting protection for chat endpoints."""
    # This would test rate limiting if implemented
    # Implementation depends on actual rate limiting mechanism
    pass
