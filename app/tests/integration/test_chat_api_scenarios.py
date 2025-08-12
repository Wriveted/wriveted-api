#!/usr/bin/env python3
"""
Enhanced integration tests for Chat API with automated scenarios.
Extracted from ad-hoc test_chat_runtime.py and improved for integration testing.
"""

import pytest
from datetime import datetime
from uuid import uuid4

from app.models.cms import (
    FlowDefinition,
    FlowNode,
    NodeType,
    CMSContent,
    ContentType,
    ConnectionType,
    FlowConnection,
)


class TestChatAPIScenarios:
    """Test comprehensive chat API scenarios."""

    @pytest.fixture
    async def sample_bookbot_flow(self, async_session):
        """Create a sample BOOKBOT-like flow for testing."""
        flow_id = uuid4()

        # Create flow definition
        flow = FlowDefinition(
            id=flow_id,
            name="BOOKBOT Test Flow",
            version="1.0",
            flow_data={},
            entry_node_id="welcome",
            is_published=True,
            is_active=True,
        )
        async_session.add(flow)

        # Create welcome message content
        welcome_content = CMSContent(
            id=uuid4(),
            type=ContentType.MESSAGE,
            content={
                "messages": [
                    {
                        "type": "text",
                        "content": "Hello! I'm BookBot. I help you discover amazing books! 📚",
                    }
                ]
            },
            is_active=True,
        )
        async_session.add(welcome_content)

        # Create question content for age
        age_question_content = CMSContent(
            id=uuid4(),
            type=ContentType.QUESTION,
            content={
                "question": "How old are you?",
                "input_type": "text",
                "variable": "temp.user_age",
            },
            is_active=True,
        )
        async_session.add(age_question_content)

        # Create question content for reading level
        reading_level_content = CMSContent(
            id=uuid4(),
            type=ContentType.QUESTION,
            content={
                "question": "What's your reading level?",
                "input_type": "choice",
                "options": ["Beginner", "Intermediate", "Advanced"],
                "variable": "temp.reading_level",
            },
            is_active=True,
        )
        async_session.add(reading_level_content)

        # Create preference question
        preference_content = CMSContent(
            id=uuid4(),
            type=ContentType.QUESTION,
            content={
                "question": "What kind of books do you like?",
                "input_type": "text",
                "variable": "temp.book_preference",
            },
            is_active=True,
        )
        async_session.add(preference_content)

        # Create recommendation message
        recommendation_content = CMSContent(
            id=uuid4(),
            type=ContentType.MESSAGE,
            content={
                "messages": [
                    {
                        "type": "text",
                        "content": "Great! Based on your preferences (age: {{temp.user_age}}, level: {{temp.reading_level}}, genre: {{temp.book_preference}}), here are some book recommendations!",
                    }
                ]
            },
            is_active=True,
        )
        async_session.add(recommendation_content)

        # Create flow nodes
        nodes = [
            FlowNode(
                flow_id=flow_id,
                node_id="welcome",
                node_type=NodeType.MESSAGE,
                content={"messages": [{"content_id": str(welcome_content.id)}]},
            ),
            FlowNode(
                flow_id=flow_id,
                node_id="ask_age",
                node_type=NodeType.QUESTION,
                content={"question": {"content_id": str(age_question_content.id)}},
            ),
            FlowNode(
                flow_id=flow_id,
                node_id="ask_reading_level",
                node_type=NodeType.QUESTION,
                content={"question": {"content_id": str(reading_level_content.id)}},
            ),
            FlowNode(
                flow_id=flow_id,
                node_id="ask_preferences",
                node_type=NodeType.QUESTION,
                content={"question": {"content_id": str(preference_content.id)}},
            ),
            FlowNode(
                flow_id=flow_id,
                node_id="show_recommendations",
                node_type=NodeType.MESSAGE,
                content={"messages": [{"content_id": str(recommendation_content.id)}]},
            ),
        ]

        for node in nodes:
            async_session.add(node)

        # Create connections between nodes
        connections = [
            FlowConnection(
                flow_id=flow_id,
                source_node_id="welcome",
                target_node_id="ask_age",
                connection_type=ConnectionType.DEFAULT,
            ),
            FlowConnection(
                flow_id=flow_id,
                source_node_id="ask_age",
                target_node_id="ask_reading_level",
                connection_type=ConnectionType.DEFAULT,
            ),
            FlowConnection(
                flow_id=flow_id,
                source_node_id="ask_reading_level",
                target_node_id="ask_preferences",
                connection_type=ConnectionType.DEFAULT,
            ),
            FlowConnection(
                flow_id=flow_id,
                source_node_id="ask_preferences",
                target_node_id="show_recommendations",
                connection_type=ConnectionType.DEFAULT,
            ),
        ]

        for connection in connections:
            async_session.add(connection)

        await async_session.commit()
        return flow_id

    async def _create_unique_flow(self, async_session, flow_name: str):
        """Helper to create a unique, BOOKBOT-like flow for isolated testing."""
        flow_id = uuid4()

        # Create flow definition
        flow = FlowDefinition(
            id=flow_id,
            name=flow_name,
            version="1.0",
            flow_data={},
            entry_node_id="welcome",
            is_published=True,
            is_active=True,
        )
        async_session.add(flow)

        # Create welcome message content
        welcome_content = CMSContent(
            id=uuid4(),
            type=ContentType.MESSAGE,
            content={
                "messages": [
                    {
                        "type": "text",
                        "content": "Hello! I'm BookBot. I help you discover amazing books! 📚",
                    }
                ]
            },
            is_active=True,
        )
        async_session.add(welcome_content)

        # Create question content for age
        age_question_content = CMSContent(
            id=uuid4(),
            type=ContentType.QUESTION,
            content={
                "question": "How old are you?",
                "input_type": "text",
                "variable": "temp.user_age",
            },
            is_active=True,
        )
        async_session.add(age_question_content)

        # Create question content for reading level
        reading_level_content = CMSContent(
            id=uuid4(),
            type=ContentType.QUESTION,
            content={
                "question": "What's your reading level?",
                "input_type": "choice",
                "options": ["Beginner", "Intermediate", "Advanced"],
                "variable": "temp.reading_level",
            },
            is_active=True,
        )
        async_session.add(reading_level_content)

        # Create preference question
        preference_content = CMSContent(
            id=uuid4(),
            type=ContentType.QUESTION,
            content={
                "question": "What kind of books do you like?",
                "input_type": "text",
                "variable": "temp.book_preference",
            },
            is_active=True,
        )
        async_session.add(preference_content)

        # Create recommendation message
        recommendation_content = CMSContent(
            id=uuid4(),
            type=ContentType.MESSAGE,
            content={
                "messages": [
                    {
                        "type": "text",
                        "content": "Great! Based on your preferences (age: {{temp.user_age}}, level: {{temp.reading_level}}, genre: {{temp.book_preference}}), here are some book recommendations!",
                    }
                ]
            },
            is_active=True,
        )
        async_session.add(recommendation_content)

        # Create flow nodes
        nodes = [
            FlowNode(
                flow_id=flow_id,
                node_id="welcome",
                node_type=NodeType.MESSAGE,
                content={"messages": [{"content_id": str(welcome_content.id)}]},
            ),
            FlowNode(
                flow_id=flow_id,
                node_id="ask_age",
                node_type=NodeType.QUESTION,
                content={"question": {"content_id": str(age_question_content.id)}},
            ),
            FlowNode(
                flow_id=flow_id,
                node_id="ask_reading_level",
                node_type=NodeType.QUESTION,
                content={"question": {"content_id": str(reading_level_content.id)}},
            ),
            FlowNode(
                flow_id=flow_id,
                node_id="ask_preferences",
                node_type=NodeType.QUESTION,
                content={"question": {"content_id": str(preference_content.id)}},
            ),
            FlowNode(
                flow_id=flow_id,
                node_id="show_recommendations",
                node_type=NodeType.MESSAGE,
                content={"messages": [{"content_id": str(recommendation_content.id)}]},
            ),
        ]

        for node in nodes:
            async_session.add(node)

        # Create connections between nodes
        connections = [
            FlowConnection(
                flow_id=flow_id,
                source_node_id="welcome",
                target_node_id="ask_age",
                connection_type=ConnectionType.DEFAULT,
            ),
            FlowConnection(
                flow_id=flow_id,
                source_node_id="ask_age",
                target_node_id="ask_reading_level",
                connection_type=ConnectionType.DEFAULT,
            ),
            FlowConnection(
                flow_id=flow_id,
                source_node_id="ask_reading_level",
                target_node_id="ask_preferences",
                connection_type=ConnectionType.DEFAULT,
            ),
            FlowConnection(
                flow_id=flow_id,
                source_node_id="ask_preferences",
                target_node_id="show_recommendations",
                connection_type=ConnectionType.DEFAULT,
            ),
        ]

        for conn in connections:
            async_session.add(conn)

        await async_session.commit()
        return flow_id

    @pytest.mark.asyncio
    async def test_automated_bookbot_conversation(
        self,
        async_client,
        sample_bookbot_flow,
        test_user_account,
        test_user_account_headers,
    ):
        """Test automated BookBot conversation scenario."""
        flow_id = sample_bookbot_flow

        # Start conversation
        start_payload = {
            "flow_id": str(flow_id),
            "user_id": str(test_user_account.id),
            "initial_state": {
                "user_context": {
                    "test_session": True,
                    "started_at": datetime.utcnow().isoformat(),
                }
            },
        }

        response = await async_client.post(
            "/v1/chat/start", json=start_payload, headers=test_user_account_headers
        )
        if response.status_code != 201:
            print(f"Unexpected status code: {response.status_code}")
            print(f"Response body: {response.text}")
        assert response.status_code == 201

        session_data = response.json()
        session_token = session_data["session_token"]
        
        # Get CSRF token from cookies, not JSON response
        csrf_token = response.cookies.get("csrf_token")
        
        # Set up CSRF protection for interact endpoint
        if csrf_token:
            async_client.cookies.set("csrf_token", csrf_token)
            interact_headers = {**test_user_account_headers, "X-CSRF-Token": csrf_token}
        else:
            interact_headers = test_user_account_headers

        # Verify initial welcome message - current node ID is in next_node.node_id
        assert session_data["next_node"]["node_id"] == "welcome"
        # Messages might be empty initially - check that we have a proper node structure
        assert "next_node" in session_data
        assert session_data["next_node"]["type"] == "messages"

        # Simple test - just verify that basic interaction works
        interact_payload = {"input": "7", "input_type": "text"}

        response = await async_client.post(
            f"/v1/chat/sessions/{session_token}/interact",
            json=interact_payload,
            headers=interact_headers,
        )

        assert response.status_code == 200
        interaction_data = response.json()

        # Basic validation - check that we got a response and are at some valid node
        assert "current_node_id" in interaction_data
        assert interaction_data["current_node_id"] is not None

        # The conversation should still be active (not ended)
        assert not interaction_data.get("session_ended", False)

        # Verify session state contains collected variables
        response = await async_client.get(
            f"/v1/chat/sessions/{session_token}", headers=test_user_account_headers
        )
        assert response.status_code == 200

        session_state = response.json()

        # Basic validation of session state structure
        assert "state" in session_state
        assert "status" in session_state
        assert session_state["status"] == "active"

        # Verify initial state was preserved
        state_vars = session_state.get("state", {})
        assert "user_context" in state_vars
        assert state_vars["user_context"]["test_session"] is True

        # Test completed successfully - basic conversation flow is working
        # This test validates:
        # 1. Session can be started with user authentication
        # 2. Basic interaction works
        # 3. Session state is preserved
        # 4. Session status remains active during conversation

    @pytest.mark.asyncio
    async def test_conversation_end_session(
        self,
        async_client,
        sample_bookbot_flow,
        test_user_account,
        test_user_account_headers,
    ):
        """Test ending a conversation session."""
        flow_id = sample_bookbot_flow

        # Start conversation
        start_payload = {
            "flow_id": str(flow_id),
            "user_id": str(test_user_account.id),
            "initial_state": {},
        }

        response = await async_client.post(
            "/v1/chat/start", json=start_payload, headers=test_user_account_headers
        )
        assert response.status_code == 201

        session_data = response.json()
        session_token = session_data["session_token"]
        
        # Get CSRF token from cookies, not JSON response
        csrf_token = response.cookies.get("csrf_token")
        
        # Set up CSRF protection for interact endpoint
        if csrf_token:
            async_client.cookies.set("csrf_token", csrf_token)
            interact_headers = {**test_user_account_headers, "X-CSRF-Token": csrf_token}
        else:
            interact_headers = test_user_account_headers

        # End session
        response = await async_client.post(
            f"/v1/chat/sessions/{session_token}/end", headers=interact_headers
        )
        assert response.status_code == 200

        # Verify session is marked as ended
        response = await async_client.get(
            f"/v1/chat/sessions/{session_token}", headers=test_user_account_headers
        )
        assert response.status_code == 200

        session_state = response.json()
        assert session_state.get("status") == "completed"

        # Verify cannot interact with ended session
        interact_payload = {"input": "test", "input_type": "text"}
        response = await async_client.post(
            f"/v1/chat/sessions/{session_token}/interact",
            json=interact_payload,
            headers=interact_headers,
        )
        assert response.status_code == 400  # Session ended

    @pytest.mark.asyncio
    async def test_session_timeout_handling(
        self,
        async_client,
        sample_bookbot_flow,
        test_user_account,
        test_user_account_headers,
    ):
        """Test session timeout and error handling."""
        flow_id = sample_bookbot_flow

        # Start conversation
        start_payload = {
            "flow_id": str(flow_id),
            "user_id": str(test_user_account.id),
            "initial_state": {},
        }

        response = await async_client.post(
            "/v1/chat/start", json=start_payload, headers=test_user_account_headers
        )
        assert response.status_code == 201

        session_data = response.json()
        session_token = session_data["session_token"]
        
        # Get CSRF token from cookies, not JSON response
        csrf_token = response.cookies.get("csrf_token")
        
        # Set up CSRF protection for interact endpoint
        if csrf_token:
            async_client.cookies.set("csrf_token", csrf_token)
            interact_headers = {**test_user_account_headers, "X-CSRF-Token": csrf_token}
        else:
            interact_headers = test_user_account_headers

        # Test invalid session token
        fake_token = "invalid_session_token"
        response = await async_client.get(
            f"/v1/chat/sessions/{fake_token}", headers=test_user_account_headers
        )
        assert response.status_code == 404

        # Test malformed interaction
        response = await async_client.post(
            f"/v1/chat/sessions/{session_token}/interact",
            json={"invalid": "payload"},
            headers=interact_headers,
        )
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_multiple_concurrent_sessions(
        self, async_client, test_user_account, test_user_account_headers, async_session
    ):
        """Test handling multiple concurrent chat sessions with isolated flows."""
        sessions = []

        # Start multiple sessions, each with its own unique flow
        for i in range(3):
            flow_id = await self._create_unique_flow(
                async_session, f"Concurrent Flow {i}"
            )

            start_payload = {
                "flow_id": str(flow_id),
                "user_id": str(test_user_account.id),
                "initial_state": {"session_number": i},
            }

            response = await async_client.post(
                "/v1/chat/start", json=start_payload, headers=test_user_account_headers
            )
            assert response.status_code == 201

            session_data = response.json()
            csrf_token = response.cookies.get("csrf_token")
            
            sessions.append({
                "token": session_data["session_token"],
                "csrf_token": csrf_token,
                "cookies": response.cookies
            })

        # Verify all sessions are independent
        for i, session_info in enumerate(sessions):
            # Include CSRF token in headers and set session-specific cookies
            if session_info["csrf_token"]:
                async_client.cookies.set("csrf_token", session_info["csrf_token"])
                headers = {**test_user_account_headers, "X-CSRF-Token": session_info["csrf_token"]}
            else:
                headers = test_user_account_headers
            
            # First interaction - move past the welcome message
            interact_payload = {
                "input": "",  # Empty input to proceed past welcome
                "input_type": "text",
            }
            
            # Set cookies for this specific request
            original_cookies = async_client.cookies
            async_client.cookies.update(session_info["cookies"])
            
            response = await async_client.post(
                f"/v1/chat/sessions/{session_info['token']}/interact",
                json=interact_payload,
                headers=headers,
            )
            
            # Restore original cookies
            async_client.cookies = original_cookies
            assert response.status_code == 200
            
            # Second interaction - answer the age question with different ages
            interact_payload = {
                "input": str(10 + i),  # Different ages
                "input_type": "text",
            }
            
            # Set cookies for this specific request
            original_cookies = async_client.cookies
            async_client.cookies.update(session_info["cookies"])
            
            response = await async_client.post(
                f"/v1/chat/sessions/{session_info['token']}/interact",
                json=interact_payload,
                headers=headers,
            )
            
            # Restore original cookies
            async_client.cookies = original_cookies
            assert response.status_code == 200

            # Verify session state is independent
            response = await async_client.get(
                f"/v1/chat/sessions/{session_info['token']}", headers=test_user_account_headers
            )
            assert response.status_code == 200

            session_state = response.json()
            state_vars = session_state.get("state", {})
            temp_vars = state_vars.get("temp", {})
            assert temp_vars.get("user_age") == str(10 + i)

        # Clean up sessions
        for session_info in sessions:
            await async_client.post(
                f"/v1/chat/sessions/{session_info['token']}/end",
                headers=test_user_account_headers,
            )

    @pytest.mark.asyncio
    async def test_variable_substitution_in_messages(
        self, async_client, test_user_account, test_user_account_headers, async_session
    ):
        """Test that variables are properly substituted in bot messages with an isolated flow."""
        flow_id = await self._create_unique_flow(
            async_session, "Variable Substitution Test Flow"
        )

        start_payload = {
            "flow_id": str(flow_id),
            "user_id": str(test_user_account.id),
            "initial_state": {},
        }

        response = await async_client.post(
            "/v1/chat/start", json=start_payload, headers=test_user_account_headers
        )
        assert response.status_code == 201
        session_data = response.json()
        session_token = session_data["session_token"]
        
        # Get CSRF token from cookies, not JSON response
        csrf_token = response.cookies.get("csrf_token")
        session_cookies = response.cookies

        # Progress through the conversation with correct input types
        interactions = [
            {"input": "", "input_type": "text"},  # Move past welcome
            {"input": "8", "input_type": "text"},  # Age
            {"input": "Advanced", "input_type": "choice"},  # Reading level
            {"input": "Science Fiction", "input_type": "text"},  # Preference
        ]

        # Include CSRF token in headers for interactions
        if csrf_token:
            async_client.cookies.set("csrf_token", csrf_token)
            interact_headers = {**test_user_account_headers, "X-CSRF-Token": csrf_token}
        else:
            interact_headers = test_user_account_headers

        for i, interaction in enumerate(interactions):
            print(f"\nDEBUG: Sending interaction {i}: {interaction}")
            # Set session cookies for each request
            original_cookies = async_client.cookies
            async_client.cookies.update(session_cookies)
            
            response = await async_client.post(
                f"/v1/chat/sessions/{session_token}/interact",
                json=interaction,
                headers=interact_headers,
            )
            
            # Restore original cookies
            async_client.cookies = original_cookies
            
            if response.status_code != 200:
                print(f"ERROR: Interaction {i} failed with status {response.status_code}: {response.text}")
            assert response.status_code == 200
            resp_json = response.json()
            print(f"DEBUG: Response {i}: current_node={resp_json.get('current_node_id')}, ended={resp_json.get('session_ended')}")
            if resp_json.get('session_ended'):
                print(f"WARNING: Session ended prematurely at interaction {i}")
            if resp_json.get('session_updated'):
                print(f"DEBUG: Session state after {i}: {resp_json['session_updated'].get('state')}")

        # Verify variable substitution in the final message
        final_response = response.json()
        print(f"DEBUG: Final response keys: {final_response.keys()}")
        print(f"DEBUG: Final response: {final_response}")
        messages = final_response.get("messages", [])
        assert len(messages) > 0, f"No messages in response: {final_response}"
        print(f"DEBUG: Messages: {messages}")
        message_content = messages[0].get("content", "")
        print(f"DEBUG: Message content: {message_content}")
        assert "8" in message_content
        assert "Advanced" in message_content
        assert "Science Fiction" in message_content
