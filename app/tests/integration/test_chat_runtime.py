"""Integration tests for the chat runtime."""

from uuid import uuid4

import pytest

from app.crud.chat_repo import chat_repo
from app.models.cms import (
    CMSContent,
    ConnectionType,
    ContentType,
    FlowConnection,
    FlowDefinition,
    FlowNode,
    NodeType,
)
from app.services.chat_runtime import chat_runtime


@pytest.mark.asyncio
async def test_message_node_processing(async_session, test_user_account):
    """Test processing a simple message node."""
    # Create a flow with a message node
    flow = FlowDefinition(
        id=uuid4(),
        name="Test Flow",
        version="1.0",
        flow_data={},
        entry_node_id="welcome",
        is_published=True,
        is_active=True,
    )
    async_session.add(flow)

    # Create content for the message
    content = CMSContent(
        id=uuid4(),
        type=ContentType.MESSAGE,
        content={"text": "Welcome {{user_name}}!"},
        is_active=True,
    )
    async_session.add(content)

    # Create message node
    message_node = FlowNode(
        flow_id=flow.id,
        node_id="welcome",
        node_type=NodeType.MESSAGE,
        content={
            "messages": [{"content_id": str(content.id), "delay": 1000}],
            "typing_indicator": True,
        },
    )
    async_session.add(message_node)

    await async_session.commit()

    # Start session
    session = await chat_runtime.start_session(
        async_session,
        flow_id=flow.id,
        user_id=test_user_account.id,
        session_token="test_token_123",
        initial_state={"user_name": "Test User"},
    )

    # Get initial node
    result = await chat_runtime.get_initial_node(async_session, flow.id, session)

    assert result["type"] == "messages"
    assert len(result["messages"]) == 1
    assert result["messages"][0]["content"]["text"] == "Welcome Test User!"
    assert result["typing_indicator"] is True


@pytest.mark.asyncio
async def test_question_node_processing(async_session, test_user_account):
    """Test processing a question node and user response."""
    # Create a flow with question and message nodes
    flow = FlowDefinition(
        id=uuid4(),
        name="Question Flow",
        version="1.0",
        flow_data={},
        entry_node_id="ask_name",
        is_published=True,
        is_active=True,
    )
    async_session.add(flow)

    # Create question content
    question_content = CMSContent(
        id=uuid4(),
        type=ContentType.QUESTION,
        content={"text": "What is your name?"},
        is_active=True,
    )
    async_session.add(question_content)

    # Create thank you content
    thanks_content = CMSContent(
        id=uuid4(),
        type=ContentType.MESSAGE,
        content={"text": "Thank you, {{name}}!"},
        is_active=True,
    )
    async_session.add(thanks_content)

    # Create nodes
    question_node = FlowNode(
        flow_id=flow.id,
        node_id="ask_name",
        node_type=NodeType.QUESTION,
        content={
            "question": {"content_id": str(question_content.id)},
            "input_type": "text",
            "variable": "name",
        },
    )
    async_session.add(question_node)

    thanks_node = FlowNode(
        flow_id=flow.id,
        node_id="thank_you",
        node_type=NodeType.MESSAGE,
        content={"messages": [{"content_id": str(thanks_content.id)}]},
    )
    async_session.add(thanks_node)

    # Create connection
    connection = FlowConnection(
        flow_id=flow.id,
        source_node_id="ask_name",
        target_node_id="thank_you",
        connection_type=ConnectionType.DEFAULT,
    )
    async_session.add(connection)

    await async_session.commit()

    # Start session
    session = await chat_runtime.start_session(
        async_session,
        flow_id=flow.id,
        user_id=test_user_account.id,
        session_token="test_token_456",
    )

    # Get initial question
    result = await chat_runtime.get_initial_node(async_session, flow.id, session)

    assert result["type"] == "question"
    assert result["question"]["content"]["text"] == "What is your name?"
    assert result["input_type"] == "text"

    # Process user response
    response = await chat_runtime.process_interaction(
        async_session, session, user_input="John Doe", input_type="text"
    )

    assert len(response["messages"]) == 1
    assert (
        response["messages"][0]["messages"][0]["content"]["text"]
        == "Thank you, John Doe!"
    )
    assert response["session_ended"] is True

    # Verify state was updated
    updated_session = await chat_repo.get_session_by_token(
        async_session, session_token="test_token_456"
    )
    assert updated_session.state["name"] == "John Doe"


@pytest.mark.asyncio
async def test_condition_node_processing(async_session, test_user_account):
    """Test condition node branching."""
    from app.services.node_processors import ConditionNodeProcessor

    # Register condition processor
    chat_runtime.register_processor(NodeType.CONDITION, ConditionNodeProcessor)

    # Create flow
    flow = FlowDefinition(
        id=uuid4(),
        name="Condition Flow",
        version="1.0",
        flow_data={},
        entry_node_id="check_age",
        is_published=True,
        is_active=True,
    )
    async_session.add(flow)

    # Create nodes
    condition_node = FlowNode(
        flow_id=flow.id,
        node_id="check_age",
        node_type=NodeType.CONDITION,
        content={
            "conditions": [
                {
                    "if": {"var": "age", "gte": 18},
                    "then": "option_0",  # Adult path
                }
            ],
            "default_path": "option_1",  # Minor path
        },
    )
    async_session.add(condition_node)

    adult_content = CMSContent(
        id=uuid4(),
        type=ContentType.MESSAGE,
        content={"text": "Welcome, adult user!"},
        is_active=True,
    )
    async_session.add(adult_content)

    adult_node = FlowNode(
        flow_id=flow.id,
        node_id="adult_message",
        node_type=NodeType.MESSAGE,
        content={"messages": [{"content_id": str(adult_content.id)}]},
    )
    async_session.add(adult_node)

    minor_content = CMSContent(
        id=uuid4(),
        type=ContentType.MESSAGE,
        content={"text": "Welcome, young user!"},
        is_active=True,
    )
    async_session.add(minor_content)

    minor_node = FlowNode(
        flow_id=flow.id,
        node_id="minor_message",
        node_type=NodeType.MESSAGE,
        content={"messages": [{"content_id": str(minor_content.id)}]},
    )
    async_session.add(minor_node)

    # Create connections
    adult_connection = FlowConnection(
        flow_id=flow.id,
        source_node_id="check_age",
        target_node_id="adult_message",
        connection_type=ConnectionType.OPTION_0,
    )
    async_session.add(adult_connection)

    minor_connection = FlowConnection(
        flow_id=flow.id,
        source_node_id="check_age",
        target_node_id="minor_message",
        connection_type=ConnectionType.OPTION_1,
    )
    async_session.add(minor_connection)

    await async_session.commit()

    # Test adult path
    session = await chat_runtime.start_session(
        async_session,
        flow_id=flow.id,
        user_id=test_user_account.id,
        session_token="test_adult",
        initial_state={"age": 25},
    )

    result = await chat_runtime.get_initial_node(async_session, flow.id, session)

    assert result["messages"][0]["content"]["text"] == "Welcome, adult user!"

    # Test minor path
    session2 = await chat_runtime.start_session(
        async_session,
        flow_id=flow.id,
        user_id=test_user_account.id,
        session_token="test_minor",
        initial_state={"age": 15},
    )

    result2 = await chat_runtime.get_initial_node(async_session, flow.id, session2)

    assert result2["messages"][0]["content"]["text"] == "Welcome, young user!"


@pytest.mark.asyncio
async def test_session_concurrency_control(async_session, test_user_account):
    """Test optimistic locking for session state updates."""
    # Create simple flow
    flow = FlowDefinition(
        id=uuid4(),
        name="Test Flow",
        version="1.0",
        flow_data={},
        entry_node_id="start",
        is_published=True,
        is_active=True,
    )
    async_session.add(flow)
    await async_session.commit()

    # Create session
    session = await chat_repo.create_session(
        async_session,
        flow_id=flow.id,
        user_id=test_user_account.id,
        session_token="concurrent_test",
        initial_state={"counter": 0},
    )

    # Simulate concurrent updates
    # First update with correct revision
    updated1 = await chat_repo.update_session_state(
        async_session,
        session_id=session.id,
        state_updates={"counter": 1},
        expected_revision=1,
    )
    assert updated1.revision == 2
    assert updated1.state["counter"] == 1

    # Second update with outdated revision should fail
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        await chat_repo.update_session_state(
            async_session,
            session_id=session.id,
            state_updates={"counter": 2},
            expected_revision=1,  # Outdated revision
        )

    # Update with correct revision should succeed
    updated2 = await chat_repo.update_session_state(
        async_session,
        session_id=session.id,
        state_updates={"counter": 2},
        expected_revision=2,
    )
    assert updated2.revision == 3
    assert updated2.state["counter"] == 2


@pytest.mark.asyncio
async def test_session_history_tracking(async_session, test_user_account):
    """Test conversation history is properly tracked."""
    # Create flow
    flow = FlowDefinition(
        id=uuid4(),
        name="History Flow",
        version="1.0",
        flow_data={},
        entry_node_id="message1",
        is_published=True,
        is_active=True,
    )
    async_session.add(flow)

    content = CMSContent(
        id=uuid4(),
        type=ContentType.MESSAGE,
        content={"text": "Test message"},
        is_active=True,
    )
    async_session.add(content)

    node = FlowNode(
        flow_id=flow.id,
        node_id="message1",
        node_type=NodeType.MESSAGE,
        content={"messages": [{"content_id": str(content.id)}]},
    )
    async_session.add(node)

    await async_session.commit()

    # Start session and process node
    session = await chat_runtime.start_session(
        async_session,
        flow_id=flow.id,
        user_id=test_user_account.id,
        session_token="history_test",
    )

    await chat_runtime.get_initial_node(async_session, flow.id, session)

    # Check history
    history = await chat_repo.get_session_history(async_session, session_id=session.id)

    assert len(history) == 1
    assert history[0].node_id == "message1"
    assert history[0].interaction_type.value == "message"
    assert history[0].content["messages"][0]["content"]["text"] == "Test message"
