"""Simple Chat API tests."""

import uuid

from starlette import status


def test_start_conversation_with_invalid_flow(client):
    """Test starting conversation with non-existent flow."""
    fake_flow_id = str(uuid.uuid4())

    session_data = {"flow_id": fake_flow_id, "user_id": str(uuid.uuid4())}

    response = client.post("v1/chat/start", json=session_data)

    assert response.status_code in [
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_404_NOT_FOUND,
    ]


def test_get_nonexistent_session(client):
    """Test retrieving non-existent session returns 404."""
    fake_token = "fake_session_token_123"

    response = client.get(f"v1/chat/sessions/{fake_token}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
