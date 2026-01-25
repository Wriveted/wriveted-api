import html
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app import crud


class FlowNotFoundError(Exception):
    """Raised when a flow is not found or not available."""

    pass


def sanitize_user_input(user_input: str) -> str:
    """Sanitize user input to prevent XSS attacks.

    SQL injection protection is handled by SQLAlchemy's parameterized queries.
    This focuses on HTML escaping for safe display in chat contexts.
    """
    return html.escape(user_input) if user_input else user_input


from app.models.cms import (
    CMSContent,
    ConnectionType,
    ContentType,
    ConversationSession,
    FlowConnection,
    FlowNode,
    InteractionType,
    NodeType,
    SessionStatus,
)
from app.repositories.chat_repository import chat_repo
from app.repositories.cms_repository import CMSRepositoryImpl
from app.services.execution_trace import execution_trace_service
from app.services.variable_resolver import create_session_resolver

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
        session_state = session.state or {}

        # Get messages from content
        message_configs = node_content.get("messages", [])

        for msg_config in message_configs:
            message = None
            content_id = msg_config.get("content_id")
            if content_id:
                # Get content from CMS
                try:
                    content = await crud.content.aget(db, UUID(content_id))
                    if content and content.is_active:
                        message = await self._render_content_message(
                            content, session_state
                        )
                except Exception as e:
                    self.logger.error(
                        "Error loading content", content_id=content_id, error=str(e)
                    )

            if message is None:
                message = self._render_inline_message(msg_config, session_state)

            if message:
                if msg_config.get("delay") is not None:
                    message["delay"] = msg_config["delay"]
                messages.append(message)

        # Fallback: check for direct "text" in node content
        if not messages and node_content.get("text"):
            raw_text = node_content["text"]
            # Apply variable substitution from session state
            rendered_text = self.runtime.substitute_variables(raw_text, session_state)
            messages.append({"type": "text", "text": rendered_text})

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
            "content": self._deep_substitute_variables(content_data, session_state),
        }
        return message

    def _render_inline_message(
        self, msg_config: Dict[str, Any], session_state: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        raw_content = None
        if "content" in msg_config:
            raw_content = msg_config.get("content")
        elif "text" in msg_config:
            raw_content = {"text": msg_config.get("text")}

        if raw_content is None:
            return None

        if isinstance(raw_content, dict):
            content = self._deep_substitute_variables(raw_content, session_state)
        else:
            content = {
                "text": self.runtime.substitute_variables(
                    str(raw_content), session_state
                )
            }

        message_type = msg_config.get("type", "text")
        return {
            "type": message_type,
            "content": content,
        }

    def _deep_substitute_variables(
        self, obj: Any, session_state: Dict[str, Any]
    ) -> Any:
        """Recursively substitute variables in nested structures."""
        if isinstance(obj, str):
            return self.runtime.substitute_variables(obj, session_state)
        elif isinstance(obj, dict):
            return {
                key: self._deep_substitute_variables(value, session_state)
                for key, value in obj.items()
            }
        elif isinstance(obj, list):
            return [
                self._deep_substitute_variables(item, session_state) for item in obj
            ]
        else:
            return obj


class QuestionNodeProcessor(NodeProcessor):
    """Processor for QUESTION nodes.

    Supports multiple content sources:
    - Inline text: Direct question text in node content
    - CMS reference: Load specific content by content_id
    - Random: Dynamically fetch random content with filtering

    For random content source, the node content format is:
    {
        "source": "random",
        "source_config": {
            "type": "question",                    # ContentType
            "tags": ["huey-preference"],           # Filter by tags
            "info_filters": {"min_age": 5},        # Filter by info JSONB
            "exclude_from": "temp.shown_ids"       # State variable with IDs to exclude
        },
        "result_variable": "temp.answer",          # Where to store user's answer
        "track_shown_in": "temp.shown_ids"         # State variable to track shown IDs
    }
    """

    async def process(
        self,
        db: AsyncSession,
        node: FlowNode,
        session: ConversationSession,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Process a question node."""
        node_content = node.content or {}
        session_state = session.state or {}
        question_message = None
        content_id = None
        fetched_content: Optional[CMSContent] = None

        # Check for random content source
        source = node_content.get("source")
        if source == "random":
            fetched_content = await self._fetch_random_content(
                db, node_content, session_state
            )
            if fetched_content:
                content_id = str(fetched_content.id)
                question_message = await self._render_question_message(
                    fetched_content, session_state
                )
                # Track shown content ID if configured
                await self._track_shown_content(
                    db, session, node_content, fetched_content.id
                )
        else:
            # Handle both CMS content references and inline content
            question_config = node_content.get("question", {})

            # Check if question is a string (inline content) or dict (CMS reference)
            if isinstance(question_config, str):
                question_message = {"text": question_config}
            elif isinstance(question_config, dict):
                # Check for inline text first
                if question_config.get("text"):
                    question_message = {"text": question_config["text"]}
                # Then check for CMS content reference
                elif question_config.get("content_id"):
                    content_id = question_config.get("content_id")

            if content_id and question_message is None:
                try:
                    content = await crud.content.aget(db, UUID(content_id))
                    if content and content.is_active:
                        question_message = await self._render_question_message(
                            content, session_state
                        )
                except Exception as e:
                    self.logger.error(
                        "Error loading question content",
                        content_id=content_id,
                        error=str(e),
                    )

        # Fallback: check for direct "text" key in node content
        if question_message is None and node_content.get("text"):
            question_message = {"text": node_content["text"]}

        # Record question in history
        await chat_repo.add_interaction_history(
            db,
            session_id=session.id,
            node_id=node.node_id,
            interaction_type=InteractionType.MESSAGE,
            content={
                "question": question_message,
                "content_id": content_id,
                "input_type": node_content.get("input_type", "text"),
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        # Determine variable for storing response
        variable = node_content.get("variable") or node_content.get("result_variable")

        return {
            "type": "question",
            "question": question_message,
            "content_id": content_id,
            "input_type": node_content.get("input_type", "text"),
            "options": node_content.get("options", []),
            "validation": node_content.get("validation", {}),
            "variable": variable,
            "node_id": node.node_id,
        }

    async def _fetch_random_content(
        self,
        db: AsyncSession,
        node_content: Dict[str, Any],
        session_state: Dict[str, Any],
    ) -> Optional[CMSContent]:
        """Fetch random content based on source_config."""
        source_config = node_content.get("source_config", {})

        # Parse content type
        content_type_str = source_config.get("type", "question")
        try:
            content_type = ContentType(content_type_str.lower())
        except ValueError:
            self.logger.error(
                "Invalid content type in source_config", content_type=content_type_str
            )
            return None

        # Get tags
        tags = source_config.get("tags")

        # Resolve info_filters with variable substitution
        info_filters = source_config.get("info_filters", {})
        resolved_filters = {}
        for key, value in info_filters.items():
            if (
                isinstance(value, str)
                and value.startswith("${")
                and value.endswith("}")
            ):
                # Resolve variable reference like "${user.age}"
                resolved_value = self.runtime.substitute_variables(value, session_state)
                if resolved_value != value:  # Successfully resolved
                    try:
                        resolved_filters[key] = int(resolved_value)
                    except (ValueError, TypeError):
                        resolved_filters[key] = resolved_value
            else:
                resolved_filters[key] = value

        # Get exclude IDs from session state
        exclude_ids = []
        exclude_from = source_config.get("exclude_from")
        if exclude_from:
            exclude_ids = self._get_state_list(session_state, exclude_from)

        # Get school_id from session context if available
        school_id = session_state.get("system", {}).get("school_id")

        try:
            cms_repo = CMSRepositoryImpl()
            content_items = await cms_repo.get_random_content(
                db=db,
                content_type=content_type,
                count=1,
                tags=tags,
                info_filters=resolved_filters if resolved_filters else None,
                exclude_ids=[UUID(eid) for eid in exclude_ids if eid]
                if exclude_ids
                else None,
                school_id=UUID(school_id) if school_id else None,
                include_public=True,
            )

            if content_items:
                self.logger.info(
                    "Fetched random content",
                    content_id=str(content_items[0].id),
                    content_type=content_type.value,
                    tags=tags,
                )
                return content_items[0]
            else:
                self.logger.warning(
                    "No random content found matching criteria",
                    content_type=content_type.value,
                    tags=tags,
                    info_filters=resolved_filters,
                )
                return None

        except Exception as e:
            self.logger.error(
                "Error fetching random content",
                error=str(e),
                content_type=content_type.value,
            )
            return None

    def _get_state_list(
        self, session_state: Dict[str, Any], variable_path: str
    ) -> List[str]:
        """Get a list from session state by variable path (e.g., 'temp.shown_ids')."""
        if "." in variable_path:
            scope, key = variable_path.split(".", 1)
            value = session_state.get(scope, {}).get(key, [])
        else:
            value = session_state.get(variable_path, [])

        if isinstance(value, list):
            return [str(v) for v in value]
        return []

    async def _track_shown_content(
        self,
        db: AsyncSession,
        session: ConversationSession,
        node_content: Dict[str, Any],
        content_id: UUID,
    ) -> None:
        """Track shown content ID in session state for deduplication."""
        track_in = node_content.get("track_shown_in")
        if not track_in:
            return

        refreshed_session = await chat_repo.get_session_by_id(db, session.id)
        if refreshed_session:
            session = refreshed_session

        # Parse variable path
        if "." in track_in:
            scope, key = track_in.split(".", 1)
        else:
            scope = "temp"
            key = track_in

        # Get current list and append new ID
        current_state = session.state or {}
        current_list = current_state.get(scope, {}).get(key, [])
        if not isinstance(current_list, list):
            current_list = []

        # Add new ID if not already present
        content_id_str = str(content_id)
        if content_id_str not in current_list:
            updated_list = current_list + [content_id_str]
            state_updates = {scope: {key: updated_list}}

            await chat_repo.update_session_state(
                db,
                session_id=session.id,
                state_updates=state_updates,
                expected_revision=session.revision,
            )
            self.logger.debug(
                "Tracked shown content ID",
                content_id=content_id_str,
                track_variable=track_in,
            )

    async def process_response(
        self,
        db: AsyncSession,
        node: FlowNode,
        session: ConversationSession,
        user_input: str,
        input_type: str,
    ) -> Dict[str, Any]:
        """Process user response to question."""
        from app.repositories.chat_repository import chat_repo

        node_content = node.content or {}
        if input_type == "text" and not user_input.strip():
            self.logger.info(
                "Empty input for question; re-asking",
                node_id=node.node_id,
            )
            return {
                "next_node": node,
                "updated_state": session.state,
                "state_was_updated": False,
                "session": session,
            }

        # Get variable name from CMS content if available
        variable_name = None
        question_config = node_content.get("question", {})

        # Handle both CMS content references and inline content
        if isinstance(question_config, str):
            # Inline question - no CMS content reference
            content_id = None
        else:
            # CMS content reference or dict config
            content_id = (
                question_config.get("content_id")
                if isinstance(question_config, dict)
                else None
            )

        if content_id:
            try:
                content = await crud.content.aget(db, UUID(content_id))
                if content and content.is_active:
                    variable_name = content.content.get("variable")
                    self.logger.debug(
                        "Got variable from CMS content",
                        content_id=content_id,
                        variable_name=variable_name,
                        cms_content=content.content,
                    )
            except Exception as e:
                self.logger.error(
                    "Error loading question content for variable",
                    content_id=content_id,
                    error=str(e),
                )

        # Fallback to node content if no CMS content variable found
        if not variable_name:
            variable_name = node_content.get("variable")

        state_was_updated = False
        self.logger.info(
            "Processing question response",
            variable_name=variable_name,
            user_input=user_input,
            node_id=node.node_id,
            content_id=content_id if content_id else "no_content_id",
        )
        if variable_name:
            # Store sanitized user input as the variable name in state
            sanitized_input = sanitize_user_input(user_input)

            # Check if variable name specifies a scope (e.g., "temp.name" or "user.age")
            if "." in variable_name:
                # Variable name already includes scope, store as-is with nested structure
                scope, var_key = variable_name.split(".", 1)
                state_updates = {scope: {var_key: sanitized_input}}
            else:
                # No scope specified, default to 'temp' scope for question responses
                state_updates = {"temp": {variable_name: sanitized_input}}

            # Update session state
            updated_session = await chat_repo.update_session_state(
                db,
                session_id=session.id,
                state_updates=state_updates,
                expected_revision=session.revision,
            )
            state_was_updated = True
            self.logger.info(
                "Updated session state",
                state_updates=state_updates,
                session_state=updated_session.state,
                full_state=updated_session.state,
                variable_name=variable_name,
            )
            # Update the session reference to the new one
            session = updated_session

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

        # Get all outgoing connections from this node for routing logic
        connections = await chat_repo.get_node_connections(
            db, flow_id=node.flow_id, source_node_id=node.node_id
        )

        # Check if any connections have conditions (indicating dynamic choice routing needed)
        has_conditional_connections = any(conn.conditions for conn in connections)

        if input_type == "button" and has_conditional_connections:
            # For button inputs with conditional connections, store the selected option value
            choice_updates = {"temp": {"user_choice": user_input}}
            updated_session = await chat_repo.update_session_state(
                db,
                session_id=session.id,
                state_updates=choice_updates,
                expected_revision=session.revision,
            )
            # Use updated session for condition evaluation
            session = updated_session

            # Find matching connection using new dynamic logic
            next_connection = await self._find_matching_connection(db, node, session)
        else:
            # For simple text inputs or button inputs without conditions, use first DEFAULT connection
            next_connection = None
            for connection in connections:
                if connection.connection_type == ConnectionType.DEFAULT:
                    next_connection = connection
                    break
            # Fallback to first connection if no DEFAULT found
            if not next_connection and connections:
                next_connection = connections[0]
        next_node = None

        if next_connection:
            next_node = await chat_repo.get_flow_node(
                db, flow_id=node.flow_id, node_id=next_connection.target_node_id
            )

        return {
            "next_node": next_node,
            "updated_state": session.state,
            "state_was_updated": state_was_updated,
            "session": session,  # Return the updated session object
        }

    async def _find_matching_connection(
        self,
        db: AsyncSession,
        node: FlowNode,
        session: ConversationSession,
    ) -> Optional[FlowConnection]:
        """Find connection that matches current session state conditions."""
        from app.crud.chat import chat_repo
        from app.services.variable_resolver import create_session_resolver

        # Get all outgoing connections from this node
        connections = await chat_repo.get_node_connections(
            db, flow_id=node.flow_id, source_node_id=node.node_id
        )

        if not connections:
            return None

        # Create variable resolver for condition evaluation
        resolver = create_session_resolver(session.state or {})

        # Try to find a connection whose conditions match
        for connection in connections:
            if connection.conditions:
                try:
                    # Evaluate condition using the current session state
                    condition_result = self._evaluate_condition(
                        connection.conditions, resolver
                    )
                    if condition_result:
                        self.logger.info(
                            "Found matching connection",
                            connection_id=connection.id,
                            conditions=connection.conditions,
                        )
                        return connection
                except Exception as e:
                    self.logger.warning(
                        "Error evaluating connection condition",
                        connection_id=connection.id,
                        conditions=connection.conditions,
                        error=str(e),
                    )
                    continue

        # If no conditions matched, try to find a DEFAULT connection
        for connection in connections:
            if (
                connection.connection_type == ConnectionType.DEFAULT
                and not connection.conditions
            ):
                return connection

        # Return first connection as fallback
        return connections[0] if connections else None

    def _evaluate_condition(self, conditions: dict, resolver) -> bool:
        """Evaluate a condition using JSONLogic-style syntax."""
        if not conditions:
            return True

        # Simple condition evaluation for {"if": {"var": "temp.user_choice", "eq": "fiction"}}
        if "if" in conditions:
            condition = conditions["if"]

            if "var" in condition and "eq" in condition:
                var_name = condition["var"]
                expected_value = condition["eq"]

                try:
                    # Use variable resolver to get the value
                    actual_value = resolver.substitute_variables(f"{{{{{var_name}}}}}")
                    # Remove the {{ }} wrapper that might remain
                    if actual_value.startswith("{{") and actual_value.endswith("}}"):
                        return False  # Variable not found
                    return str(actual_value) == str(expected_value)
                except Exception:
                    return False

        return False

    async def _render_question_message(
        self, content, session_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Render question content with variable substitution."""
        content_data = content.content or {}
        message = {
            "id": str(content.id),
            "type": content.type.value,
            "content": self._deep_substitute_variables(content_data, session_state),
        }
        return message

    def _deep_substitute_variables(
        self, obj: Any, session_state: Dict[str, Any]
    ) -> Any:
        """Recursively substitute variables in nested structures."""
        if isinstance(obj, str):
            return self.runtime.substitute_variables(obj, session_state)
        elif isinstance(obj, dict):
            return {
                key: self._deep_substitute_variables(value, session_state)
                for key, value in obj.items()
            }
        elif isinstance(obj, list):
            return [
                self._deep_substitute_variables(item, session_state) for item in obj
            ]
        else:
            return obj


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
        from app.services.action_processor import ActionNodeProcessor
        from app.services.node_processors import (
            CompositeNodeProcessor,
            ConditionNodeProcessor,
            ScriptNodeProcessor,
            WebhookNodeProcessor,
        )

        self.register_processor(NodeType.CONDITION, ConditionNodeProcessor)
        self.register_processor(NodeType.ACTION, ActionNodeProcessor)
        self.register_processor(NodeType.WEBHOOK, WebhookNodeProcessor)
        self.register_processor(NodeType.COMPOSITE, CompositeNodeProcessor)
        self.register_processor(NodeType.SCRIPT, ScriptNodeProcessor)

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
            raise FlowNotFoundError("Flow not found or not available")

        # Generate session token if not provided
        if session_token is None:
            import secrets

            session_token = secrets.token_urlsafe(32)

        trace_enabled = await execution_trace_service.should_trace_session(
            db=db, flow_id=flow_id, session_token=session_token
        )
        trace_level = execution_trace_service.get_trace_level(flow).value

        # Create session with flow version for historical tracking
        session = await chat_repo.create_session(
            db,
            flow_id=flow_id,
            user_id=user_id,
            session_token=session_token,
            initial_state=initial_state,
            flow_version=flow.version,
            trace_enabled=trace_enabled,
            trace_level=trace_level,
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
        state_before = execution_trace_service.efficient_state_copy(session.state or {})
        started_at = datetime.utcnow()
        start_time = time.perf_counter()
        result: Optional[Dict[str, Any]] = None
        updated_session = session
        error: Optional[Exception] = None

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
            updated_session = await chat_repo.update_session_state(
                db,
                session_id=session.id,
                state_updates={},  # No state changes, just update activity
                current_node_id=node.node_id,
            )

            return result

        except Exception as e:
            error = e
            self.logger.error(
                "Error processing node",
                node_id=node.node_id,
                node_type=node.node_type,
                error=str(e),
            )
            raise
        finally:
            completed_at = datetime.utcnow()
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            state_after = execution_trace_service.efficient_state_copy(
                updated_session.state or {}
            )
            await self._record_trace_safe(
                db=db,
                session=updated_session,
                node=node,
                state_before=state_before,
                state_after=state_after,
                result=result,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=duration_ms,
                error=error,
            )

    async def _record_trace_safe(
        self,
        *,
        db: AsyncSession,
        session: ConversationSession,
        node: FlowNode,
        state_before: Dict[str, Any],
        state_after: Dict[str, Any],
        result: Optional[Dict[str, Any]],
        started_at: datetime,
        completed_at: datetime,
        duration_ms: int,
        error: Optional[Exception] = None,
    ) -> None:
        """Record a trace step without impacting chat execution."""
        if not session.trace_enabled:
            return

        try:
            step_number = await execution_trace_service.get_next_step_number(
                db=db, session_id=session.id
            )
            node_type_value = (
                node.node_type.value
                if hasattr(node.node_type, "value")
                else str(node.node_type)
            )
            serialized_result = self._serialize_node_result(result) if result else {}
            execution_details = execution_trace_service.build_execution_details(
                node_type=node_type_value,
                result=serialized_result,
                node_content=node.content or {},
            )
            connection_type = (
                serialized_result.get("connection_type")
                if isinstance(serialized_result, dict)
                else None
            )
            next_node_id = None
            if isinstance(serialized_result, dict):
                next_node = serialized_result.get("next_node")
                if isinstance(next_node, FlowNode):
                    next_node_id = next_node.node_id
                elif isinstance(next_node, dict):
                    next_node_id = next_node.get("node_id") or next_node.get("id")
                elif serialized_result.get("next_node_id"):
                    next_node_id = serialized_result.get("next_node_id")

            error_message = str(error) if error else None
            error_details = (
                {"type": type(error).__name__} if error is not None else None
            )

            await execution_trace_service.record_step_async(
                session_id=session.id,
                node_id=node.node_id,
                node_type=node_type_value,
                step_number=step_number,
                state_before=state_before,
                state_after=state_after,
                execution_details=execution_details,
                connection_type=connection_type,
                next_node_id=next_node_id,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=duration_ms,
                error_message=error_message,
                error_details=error_details,
            )
        except Exception as trace_error:
            self.logger.error(
                "Trace recording failed silently",
                session_id=session.id,
                node_id=node.node_id,
                error=str(trace_error),
            )

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
        # Use current_flow_id if set (for sub-flow support), otherwise use main flow_id
        lookup_flow_id = session.current_flow_id or session.flow_id
        current_node = None
        if session.current_node_id:
            current_node = await chat_repo.get_flow_node(
                db, flow_id=lookup_flow_id, node_id=cast(str, session.current_node_id)
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

        self.logger.info(
            "Processing interaction",
            current_node_id=current_node.node_id,
            node_type=current_node.node_type,
        )

        if current_node.node_type == NodeType.QUESTION:
            # Process question response
            processor = QuestionNodeProcessor(self)
            response = await processor.process_response(
                db, current_node, session, user_input, input_type
            )

            # Get updated session state if available
            if response.get("state_was_updated", False):
                # Use the updated session from the response
                if response.get("session"):
                    session = response["session"]
                    result["session_updated"] = {
                        "state": session.state,
                        "revision": session.revision,
                    }
                else:
                    # Fallback: Refresh session from database to get latest state
                    updated_session = await chat_repo.get_session_by_token(
                        db, session.session_token
                    )
                    if updated_session:
                        session = updated_session
                        result["session_updated"] = {
                            "state": session.state,
                            "revision": session.revision,
                        }

            # Process next node if available
            if response.get("next_node"):
                awaiting_input = False
                next_result = await self.process_node(
                    db, response["next_node"], session
                )
                session = await self._refresh_session(db, session)
                # Extract messages from result if it's a messages-type response,
                # otherwise wrap the result in a list for consistency
                if next_result and next_result.get("type") == "messages":
                    result["messages"] = next_result.get("messages", [])
                else:
                    result["messages"] = [next_result] if next_result else []

                # Determine the correct session position:
                # If the processed node (e.g., message) has a next_node that's a question,
                # position the session at that question node so user input goes there
                session_position = response["next_node"].node_id
                session_flow_id: Optional[UUID] = None
                chained_next_node = (
                    next_result.get("next_node") if next_result else None
                )
                if response["next_node"].node_type == NodeType.QUESTION or (
                    isinstance(next_result, dict)
                    and next_result.get("type") == "question"
                ):
                    awaiting_input = True
                if chained_next_node:
                    # Handle FlowNode objects
                    if isinstance(chained_next_node, FlowNode):
                        if chained_next_node.node_type == NodeType.QUESTION:
                            session_position = chained_next_node.node_id
                            session_flow_id = chained_next_node.flow_id
                            awaiting_input = True
                    # Handle dict results (e.g., from composite node sub-flows)
                    elif isinstance(chained_next_node, dict):
                        if chained_next_node.get("type") == "question":
                            node_id = chained_next_node.get("node_id")
                            if node_id:
                                session_position = node_id
                                # Get sub_flow_id from the parent result (composite node)
                                sub_flow_id = next_result.get("sub_flow_id")
                                if sub_flow_id:
                                    session_flow_id = (
                                        UUID(sub_flow_id)
                                        if isinstance(sub_flow_id, str)
                                        else sub_flow_id
                                    )
                                awaiting_input = True

                result["current_node_id"] = session_position

                # Update session's current node position (and flow for sub-flow support)
                session = await chat_repo.update_session_state(
                    db,
                    session_id=session.id,
                    state_updates={},  # No state changes, just position update
                    current_node_id=session_position,
                    current_flow_id=session_flow_id,
                    expected_revision=session.revision,
                )

                # Continue processing through non-interactive nodes (action, condition)
                # until we hit a question node or the flow ends
                while chained_next_node:
                    # If next node is a FlowNode
                    if isinstance(chained_next_node, FlowNode):
                        if chained_next_node.node_type == NodeType.QUESTION:
                            # Stop at question - already handled above
                            session_position = chained_next_node.node_id
                            session_flow_id = chained_next_node.flow_id
                            session = await self._refresh_session(db, session)
                            session = await chat_repo.update_session_state(
                                db,
                                session_id=session.id,
                                state_updates={},
                                current_node_id=session_position,
                                current_flow_id=session_flow_id,
                                expected_revision=session.revision,
                            )
                            awaiting_input = True
                            break
                        elif chained_next_node.node_type in (
                            NodeType.ACTION,
                            NodeType.CONDITION,
                        ):
                            # Process action/condition automatically
                            auto_result = await self.process_node(
                                db, chained_next_node, session
                            )
                            session = await self._refresh_session(db, session)
                            # Collect any messages from the auto-processed result
                            if auto_result and auto_result.get("type") == "messages":
                                result["messages"].extend(
                                    auto_result.get("messages", [])
                                )
                            # Update position and continue
                            session_position = chained_next_node.node_id
                            session_flow_id = chained_next_node.flow_id
                            chained_next_node = auto_result.get("next_node")

                            # Update session position
                            session = await chat_repo.update_session_state(
                                db,
                                session_id=session.id,
                                state_updates={},
                                current_node_id=session_position,
                                current_flow_id=session_flow_id,
                                expected_revision=session.revision,
                            )
                        elif chained_next_node.node_type == NodeType.MESSAGE:
                            # Process message and check what comes after
                            msg_result = await self.process_node(
                                db, chained_next_node, session
                            )
                            session = await self._refresh_session(db, session)
                            # Extract and append actual messages from the result
                            if msg_result and msg_result.get("type") == "messages":
                                result["messages"].extend(
                                    msg_result.get("messages", [])
                                )
                            elif msg_result:
                                result["messages"].append(msg_result)
                            session_position = chained_next_node.node_id
                            session_flow_id = chained_next_node.flow_id
                            chained_next_node = (
                                msg_result.get("next_node") if msg_result else None
                            )

                            # Update session position
                            session = await chat_repo.update_session_state(
                                db,
                                session_id=session.id,
                                state_updates={},
                                current_node_id=session_position,
                                current_flow_id=session_flow_id,
                                expected_revision=session.revision,
                            )
                        else:
                            # Unknown node type, stop processing
                            break
                    else:
                        # Dict result (like from composite) - already handled
                        break

                result["current_node_id"] = session_position

                # Check if the flow ended (no more next nodes)
                if not chained_next_node and not awaiting_input:
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
                    session = await self._refresh_session(db, session)
                    result["messages"] = [next_result] if next_result else []

                    # Determine session position: if the processed node's next_node is a QUESTION,
                    # position the session at that QUESTION so user input goes there
                    session_position = next_node.node_id
                    chained_next = next_result.get("next_node") if next_result else None
                    if chained_next and isinstance(chained_next, FlowNode):
                        if chained_next.node_type == NodeType.QUESTION:
                            session_position = chained_next.node_id

                    result["current_node_id"] = session_position

                    # Update session's current node position
                    session = await chat_repo.update_session_state(
                        db,
                        session_id=session.id,
                        state_updates={},  # No state changes, just position update
                        current_node_id=session_position,
                        expected_revision=session.revision,
                    )
                else:
                    result["session_ended"] = True
            else:
                result["session_ended"] = True

        # Check for parent flow return before ending session
        if result["session_ended"]:
            return_result = await self._try_return_to_parent_flow(db, session, result)
            if return_result:
                # Successfully returned to parent flow
                return self._serialize_node_result(return_result)
            # No parent flow to return to, end the session
            await chat_repo.end_session(
                db, session_id=session.id, status=SessionStatus.COMPLETED
            )

        # Serialize any FlowNode objects in the result
        return self._serialize_node_result(result)

    async def _try_return_to_parent_flow(
        self,
        db: AsyncSession,
        session: ConversationSession,
        current_result: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Check if we're in a sub-flow and return to parent flow if applicable.

        When a sub-flow completes (no next node), this method checks if there's
        a parent flow context in the session's flow_stack. If so, it pops the
        context and continues from the parent flow's return node.

        Returns:
            Updated result dict if returning to parent flow, None if no parent.
        """
        # Refresh session to get latest info
        session = await self._refresh_session(db, session)

        flow_stack = session.info.get("flow_stack", [])
        if not flow_stack:
            return None

        # Pop the parent flow context
        parent_context = flow_stack.pop()
        parent_flow_id = parent_context.get("parent_flow_id")
        return_node_id = parent_context.get("return_node_id")

        self.logger.info(
            "Returning to parent flow from sub-flow",
            parent_flow_id=parent_flow_id,
            return_node_id=return_node_id,
            remaining_stack_depth=len(flow_stack),
        )

        # Update session with parent flow context
        from sqlalchemy.orm.attributes import flag_modified

        session.info["flow_stack"] = flow_stack
        flag_modified(session, "info")

        parent_flow_uuid = UUID(parent_flow_id) if parent_flow_id else session.flow_id

        session = await chat_repo.update_session_state(
            db,
            session_id=session.id,
            state_updates={},
            current_flow_id=parent_flow_uuid,
            current_node_id=return_node_id,
            expected_revision=session.revision,
        )

        if not return_node_id:
            # No return node defined, check if we can pop another level
            if flow_stack:
                return await self._try_return_to_parent_flow(
                    db, session, current_result
                )
            return None

        # Get the return node and process it
        return_node = await chat_repo.get_flow_node(
            db, flow_id=parent_flow_uuid, node_id=return_node_id
        )

        if not return_node:
            self.logger.warning(
                "Return node not found in parent flow",
                parent_flow_id=parent_flow_id,
                return_node_id=return_node_id,
            )
            return None

        # Combine messages from sub-flow completion with parent continuation
        result = {
            "messages": current_result.get("messages", []),
            "session_ended": False,
            "returned_from_subflow": True,
        }

        # Process the return node
        return_result = await self.process_node(db, return_node, session)
        session = await self._refresh_session(db, session)

        if return_result:
            if return_result.get("type") == "messages":
                result["messages"].append(return_result)
            else:
                result["messages"].append(return_result)

            # Continue processing chain until question or end
            next_node = return_result.get("next_node")
            while next_node:
                if isinstance(next_node, FlowNode):
                    if next_node.node_type == NodeType.QUESTION:
                        # Update session position to question
                        session = await chat_repo.update_session_state(
                            db,
                            session_id=session.id,
                            state_updates={},
                            current_node_id=next_node.node_id,
                            current_flow_id=next_node.flow_id,
                            expected_revision=session.revision,
                        )
                        result["current_node_id"] = next_node.node_id
                        result["awaiting_input"] = True
                        break
                    elif next_node.node_type in (
                        NodeType.MESSAGE,
                        NodeType.ACTION,
                        NodeType.CONDITION,
                    ):
                        node_result = await self.process_node(db, next_node, session)
                        session = await self._refresh_session(db, session)
                        if node_result:
                            result["messages"].append(node_result)
                        next_node = (
                            node_result.get("next_node") if node_result else None
                        )
                    else:
                        break
                else:
                    break

            # If no next node after processing, check for another parent level
            if not next_node and not result.get("awaiting_input"):
                result["session_ended"] = True
                # Recursively check for more parent flows
                if flow_stack:
                    return await self._try_return_to_parent_flow(db, session, result)

        return result

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

            # If the entry node is a message leading into a question, advance position
            next_node = result.get("next_node")
            if next_node and isinstance(next_node, FlowNode):
                if next_node.node_type == NodeType.QUESTION:
                    await chat_repo.update_session_state(
                        db,
                        session_id=session.id,
                        state_updates={},
                        current_node_id=next_node.node_id,
                    )

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
                    else (
                        self._serialize_node_result(item)
                        if isinstance(item, dict)
                        else item
                    )
                    for item in value
                ]
            elif isinstance(value, dict):
                serialized[key] = self._serialize_node_result(value)

        return serialized

    async def _refresh_session(
        self, db: AsyncSession, session: ConversationSession
    ) -> ConversationSession:
        """Refresh session to keep revision current after state updates."""
        refreshed = await chat_repo.get_session_by_id(db, session.id)
        return refreshed or session

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


def reset_chat_runtime() -> None:
    """Reset the global chat runtime instance for testing."""
    global chat_runtime
    chat_runtime = ChatRuntime()
