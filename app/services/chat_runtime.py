from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app import crud
from app.crud.chat_repo import chat_repo
from app.models.cms import (
    ConnectionType,
    ConversationSession,
    FlowConnection,
    FlowNode,
    InteractionType,
    NodeType,
    SessionStatus,
)
from app.services.variable_resolver import VariableResolver, create_session_resolver

logger = get_logger()


class NodeProcessor(ABC):
    """Abstract base class for node processors."""

    def __init__(self, runtime: "ChatRuntime"):
        self.runtime = runtime
        self.logger = logger

    @abstractmethod
    async def process(
        self,
        db: AsyncSession,
        node: FlowNode,
        session: ConversationSession,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Process a node and return the result."""
        pass

    async def get_next_connection(
        self,
        db: AsyncSession,
        node: FlowNode,
        connection_type: ConnectionType = ConnectionType.DEFAULT,
    ) -> Optional[FlowConnection]:
        """Get the next connection from current node."""
        connections = await chat_repo.get_node_connections(
            db, flow_id=node.flow_id, source_node_id=node.node_id
        )

        # Try to find specific connection type
        for conn in connections:
            if conn.connection_type == connection_type:
                return conn

        # Fall back to default if not found
        if connection_type != ConnectionType.DEFAULT:
            for conn in connections:
                if conn.connection_type == ConnectionType.DEFAULT:
                    return conn

        return None


class MessageNodeProcessor(NodeProcessor):
    """Processor for MESSAGE nodes."""

    async def process(
        self,
        db: AsyncSession,
        node: FlowNode,
        session: ConversationSession,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Process a message node."""
        node_content = node.content or {}
        messages = []

        # Get messages from content
        message_configs = node_content.get("messages", [])

        for msg_config in message_configs:
            content_id = msg_config.get("content_id")
            if content_id:
                # Get content from CMS
                try:
                    content = await crud.content.aget(db, UUID(content_id))
                    if content and content.is_active:
                        message = await self._render_content_message(
                            content, session.state or {}
                        )
                        if msg_config.get("delay"):
                            message["delay"] = msg_config["delay"]
                        messages.append(message)
                except Exception as e:
                    self.logger.error(
                        "Error loading content", content_id=content_id, error=str(e)
                    )

        # Record the message in history
        await chat_repo.add_interaction_history(
            db,
            session_id=session.id,
            node_id=node.node_id,
            interaction_type=InteractionType.MESSAGE,
            content={"messages": messages, "timestamp": datetime.utcnow().isoformat()},
        )

        # Get next node
        next_connection = await self.get_next_connection(db, node)
        next_node = None

        if next_connection:
            next_node = await chat_repo.get_flow_node(
                db, flow_id=node.flow_id, node_id=next_connection.target_node_id
            )

        return {
            "type": "messages",
            "messages": messages,
            "typing_indicator": node_content.get("typing_indicator", True),
            "node_id": node.node_id,
            "next_node": next_node,
            "wait_for_acknowledgment": node_content.get("wait_for_ack", False),
        }

    async def _render_content_message(
        self, content, session_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Render content message with variable substitution."""
        content_data = content.content or {}
        message = {
            "id": str(content.id),
            "type": content.type.value,
            "content": content_data.copy(),
        }

        # Perform variable substitution
        for key, value in content_data.items():
            if isinstance(value, str):
                message["content"][key] = self.runtime.substitute_variables(
                    value, session_state
                )

        return message


class QuestionNodeProcessor(NodeProcessor):
    """Processor for QUESTION nodes."""

    async def process(
        self,
        db: AsyncSession,
        node: FlowNode,
        session: ConversationSession,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Process a question node."""
        node_content = node.content or {}

        # Get question content
        question_config = node_content.get("question", {})
        content_id = question_config.get("content_id")

        question_message = None
        if content_id:
            try:
                content = await crud.content.aget(db, UUID(content_id))
                if content and content.is_active:
                    question_message = await self._render_question_message(
                        content, session.state or {}
                    )
            except Exception as e:
                self.logger.error(
                    "Error loading question content",
                    content_id=content_id,
                    error=str(e),
                )

        # Record question in history
        await chat_repo.add_interaction_history(
            db,
            session_id=session.id,
            node_id=node.node_id,
            interaction_type=InteractionType.MESSAGE,
            content={
                "question": question_message,
                "input_type": node_content.get("input_type", "text"),
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        return {
            "type": "question",
            "question": question_message,
            "input_type": node_content.get("input_type", "text"),
            "options": node_content.get("options", []),
            "validation": node_content.get("validation", {}),
            "variable": node_content.get("variable"),  # Variable to store response
            "node_id": node.node_id,
        }

    async def process_response(
        self,
        db: AsyncSession,
        node: FlowNode,
        session: ConversationSession,
        user_input: str,
        input_type: str,
    ) -> Dict[str, Any]:
        """Process user response to question."""
        node_content = node.content or {}

        # Store response in session state if variable is specified
        variable_name = node_content.get("variable")
        if variable_name:
            # Store user input in temp scope for proper variable resolution
            temp_scope = session.state.get("temp", {})
            temp_scope[variable_name] = user_input
            state_updates = {"temp": temp_scope}

            # Update session state
            session = await chat_repo.update_session_state(
                db,
                session_id=session.id,
                state_updates=state_updates,
                expected_revision=session.revision,
            )

        # Record user input in history
        await chat_repo.add_interaction_history(
            db,
            session_id=session.id,
            node_id=node.node_id,
            interaction_type=InteractionType.INPUT,
            content={
                "input": user_input,
                "input_type": input_type,
                "variable": variable_name,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        # Determine next connection based on input
        connection_type = ConnectionType.DEFAULT

        if input_type == "button":
            # Check if it matches predefined options
            options = node_content.get("options", [])
            for i, option in enumerate(options):
                if (
                    option.get("payload") == user_input
                    or option.get("value") == user_input
                ):
                    if i == 0:
                        connection_type = ConnectionType.OPTION_0
                    elif i == 1:
                        connection_type = ConnectionType.OPTION_1
                    break

        # Get next node
        next_connection = await self.get_next_connection(db, node, connection_type)
        next_node = None

        if next_connection:
            next_node = await chat_repo.get_flow_node(
                db, flow_id=node.flow_id, node_id=next_connection.target_node_id
            )

        return {"next_node": next_node, "updated_state": session.state}

    async def _render_question_message(
        self, content, session_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Render question content with variable substitution."""
        content_data = content.content or {}
        message = {
            "id": str(content.id),
            "type": content.type.value,
            "content": content_data.copy(),
        }

        # Perform variable substitution
        for key, value in content_data.items():
            if isinstance(value, str):
                message["content"][key] = self.runtime.substitute_variables(
                    value, session_state
                )

        return message


class ChatRuntime:
    """Main chat runtime engine with node processor registration."""

    def __init__(self):
        self.logger = logger
        self.node_processors: Dict[NodeType, Type[NodeProcessor]] = {}
        self._register_processors()

    def _register_processors(self):
        """Register default node processors."""
        self.register_processor(NodeType.MESSAGE, MessageNodeProcessor)
        self.register_processor(NodeType.QUESTION, QuestionNodeProcessor)

        # Register additional processors lazily
        self._additional_processors_registered = False

    def register_processor(
        self, node_type: NodeType, processor_class: Type[NodeProcessor]
    ):
        """Register a node processor for a specific node type."""
        self.node_processors[node_type] = processor_class

    def _register_additional_processors(self):
        """Lazily register additional node processors."""
        from app.services.node_processors import (
            ActionNodeProcessor,
            CompositeNodeProcessor,
            ConditionNodeProcessor,
            WebhookNodeProcessor,
        )

        self.register_processor(NodeType.CONDITION, ConditionNodeProcessor)
        self.register_processor(NodeType.ACTION, ActionNodeProcessor)
        self.register_processor(NodeType.WEBHOOK, WebhookNodeProcessor)
        self.register_processor(NodeType.COMPOSITE, CompositeNodeProcessor)

        self._additional_processors_registered = True

    async def start_session(
        self,
        db: AsyncSession,
        flow_id: UUID,
        user_id: Optional[UUID] = None,
        session_token: Optional[str] = None,
        initial_state: Optional[Dict[str, Any]] = None,
    ) -> ConversationSession:
        """Start a new conversation session."""
        # Get flow definition
        flow = await crud.flow.aget(db, flow_id)
        if not flow or not flow.is_published or not flow.is_active:
            raise ValueError("Flow not found or not available")

        # Generate session token if not provided
        if session_token is None:
            import secrets

            session_token = secrets.token_urlsafe(32)

        # Create session
        session = await chat_repo.create_session(
            db,
            flow_id=flow_id,
            user_id=user_id,
            session_token=session_token,
            initial_state=initial_state,
        )

        self.logger.info(
            "Started conversation session",
            session_id=session.id,
            flow_id=flow_id,
            user_id=user_id,
        )

        return session

    async def process_node(
        self,
        db: AsyncSession,
        node: FlowNode,
        session: ConversationSession,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Process a node using the appropriate processor."""
        # Lazy load additional processors if needed
        if (
            not self._additional_processors_registered
            and node.node_type not in self.node_processors
        ):
            self._register_additional_processors()

        processor_class = self.node_processors.get(node.node_type)

        if not processor_class:
            self.logger.warning(
                "No processor registered for node type",
                node_type=node.node_type,
                node_id=node.node_id,
            )
            return {
                "type": "error",
                "error": f"No processor for node type: {node.node_type}",
            }

        processor = processor_class(self)
        context = context or {}

        try:
            result = await processor.process(db, node, session, context)

            # Update session's current node
            await chat_repo.update_session_state(
                db,
                session_id=session.id,
                state_updates={},  # No state changes, just update activity
                current_node_id=node.node_id,
            )

            return result

        except Exception as e:
            self.logger.error(
                "Error processing node",
                node_id=node.node_id,
                node_type=node.node_type,
                error=str(e),
            )
            raise

    async def process_interaction(
        self,
        db: AsyncSession,
        session: ConversationSession,
        user_input: str,
        input_type: str = "text",
    ) -> Dict[str, Any]:
        """Process user interaction based on current node."""
        if session.status != SessionStatus.ACTIVE:
            raise ValueError("Session is not active")

        # Get current node
        current_node = None
        if session.current_node_id:
            current_node = await chat_repo.get_flow_node(
                db, flow_id=session.flow_id, node_id=cast(str, session.current_node_id)
            )

        if not current_node:
            # Start from entry node if no current node
            flow = await crud.flow.aget(db, session.flow_id)
            if flow:
                current_node = await chat_repo.get_flow_node(
                    db, flow_id=session.flow_id, node_id=flow.entry_node_id
                )

        if not current_node:
            raise ValueError("Cannot find current node")

        # Process based on node type
        result = {"messages": [], "session_ended": False}

        if current_node.node_type == NodeType.QUESTION:
            # Process question response
            processor = QuestionNodeProcessor(self)
            response = await processor.process_response(
                db, current_node, session, user_input, input_type
            )

            # Process next node if available
            if response.get("next_node"):
                next_result = await self.process_node(
                    db, response["next_node"], session
                )
                result["messages"] = [next_result] if next_result else []
                result["current_node_id"] = response["next_node"].node_id

                # Check if the processed node has no further connections
                if next_result and not next_result.get("next_node"):
                    result["session_ended"] = True
            else:
                result["session_ended"] = True

        elif current_node.node_type == NodeType.MESSAGE:
            # For message nodes, just continue to next
            processor = MessageNodeProcessor(self)
            next_connection = await processor.get_next_connection(db, current_node)

            if next_connection:
                next_node = await chat_repo.get_flow_node(
                    db,
                    flow_id=current_node.flow_id,
                    node_id=next_connection.target_node_id,
                )
                if next_node:
                    next_result = await self.process_node(db, next_node, session)
                    result["messages"] = [next_result] if next_result else []
                    result["current_node_id"] = next_node.node_id
                else:
                    result["session_ended"] = True
            else:
                result["session_ended"] = True

        # End session if needed
        if result["session_ended"]:
            await chat_repo.end_session(
                db, session_id=session.id, status=SessionStatus.COMPLETED
            )

        # Serialize any FlowNode objects in the result
        return self._serialize_node_result(result)

    async def get_initial_node(
        self, db: AsyncSession, flow_id: UUID, session: ConversationSession
    ) -> Optional[Dict[str, Any]]:
        """Get the initial node for a flow."""
        flow = await crud.flow.aget(db, flow_id)
        if not flow:
            return None

        entry_node = await chat_repo.get_flow_node(
            db, flow_id=flow_id, node_id=flow.entry_node_id
        )

        if entry_node:
            result = await self.process_node(db, entry_node, session)
            # Ensure any FlowNode objects are serialized
            return self._serialize_node_result(result)

        return None

    def _serialize_node_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize node processing result, converting FlowNode objects to dicts."""
        if result is None:
            return None

        serialized = result.copy()

        # Convert FlowNode objects to dictionaries
        for key, value in result.items():
            if isinstance(value, FlowNode):
                serialized[key] = self._flow_node_to_dict(value)
            elif isinstance(value, list):
                serialized[key] = [
                    self._flow_node_to_dict(item)
                    if isinstance(item, FlowNode)
                    else item
                    for item in value
                ]
            elif isinstance(value, dict):
                serialized[key] = self._serialize_node_result(value)

        return serialized

    def _flow_node_to_dict(self, node: FlowNode) -> Dict[str, Any]:
        """Convert FlowNode to dictionary for API serialization."""
        return {
            "id": str(node.id),
            "node_id": node.node_id,
            "node_type": node.node_type.value,
            "content": node.content,
            "position": node.position,
        }

    def substitute_variables(
        self,
        text: str,
        session_state: Dict[str, Any],
        composite_scopes: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> str:
        """
        Substitute variables in text using enhanced variable resolver.

        Args:
            text: Text containing variable references
            session_state: Current session state
            composite_scopes: Additional scopes for composite nodes (input, output, local)

        Returns:
            Text with variables substituted
        """
        resolver = create_session_resolver(session_state, composite_scopes)
        return resolver.substitute_variables(text, preserve_unresolved=True)

    def substitute_object(
        self,
        obj: Any,
        session_state: Dict[str, Any],
        composite_scopes: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Any:
        """
        Substitute variables in complex objects (dicts, lists, etc.).

        Args:
            obj: Object to process
            session_state: Current session state
            composite_scopes: Additional scopes for composite nodes

        Returns:
            Object with variables substituted
        """
        resolver = create_session_resolver(session_state, composite_scopes)
        return resolver.substitute_object(obj, preserve_unresolved=True)

    def validate_variables(
        self,
        text: str,
        session_state: Dict[str, Any],
        composite_scopes: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> List[str]:
        """
        Validate all variable references in text.

        Args:
            text: Text to validate
            session_state: Current session state
            composite_scopes: Additional scopes for composite nodes

        Returns:
            List of validation error messages
        """
        resolver = create_session_resolver(session_state, composite_scopes)
        return resolver.validate_variable_references(text)

    def _get_nested_value(self, data: Dict[str, Any], key_path: str) -> Any:
        """Get nested value from dictionary using dot notation."""
        keys = key_path.split(".")
        value = data

        try:
            for key in keys:
                if isinstance(value, dict):
                    value = value.get(key)
                else:
                    return None
            return value
        except (KeyError, TypeError):
            return None


# Create singleton instance
chat_runtime = ChatRuntime()
