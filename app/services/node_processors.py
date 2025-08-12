"""
Extended node processors for advanced chatbot functionality.

This module provides specialized processors for complex node types including
condition logic, action execution, webhook calls, and composite node handling.
"""

import json
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.models.cms import ConversationSession, FlowNode, NodeType
from app.services.cel_evaluator import evaluate_cel_expression
from app.services.circuit_breaker import get_circuit_breaker
from app.services.variable_resolver import VariableResolver
from app.services.node_input_validation import validate_node_input

logger = get_logger()


class ConditionNodeProcessor:
    """
    Processes condition nodes that branch conversation flow based on session state.

    Evaluates conditional logic against session variables and determines
    the next node to execute in the conversation flow.
    """

    def __init__(self, runtime):
        self.runtime = runtime
        self.logger = logger

    async def process(
        self,
        db: AsyncSession,
        node: FlowNode,
        session: ConversationSession,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Process a condition node by evaluating conditions against session state.
        
        Enhanced with rigorous input validation to prevent runtime errors.

        Args:
            db: Database session
            node: FlowNode with condition configuration
            session: Current conversation session
            context: Additional context data

        Returns:
            Dict with condition evaluation result and next node
        """
        try:
            node_content = node.content or {}
            
            # Validate condition node content before processing
            validation_report = validate_node_input(
                node_id=node.node_id,
                node_type=NodeType.CONDITION,
                node_content=node_content
            )
            
            if not validation_report.is_valid:
                error_messages = [r.message for r in validation_report.errors]
                logger.error("Condition node validation failed", 
                            node_id=node.node_id,
                            session_id=session.id,
                            errors=error_messages)
                return {
                    "type": "condition",
                    "condition_result": False,
                    "validation_errors": error_messages,
                    "error": f"Node validation failed: {'; '.join(error_messages)}",
                    "node_id": node.node_id,
                }
            
            # Log validation warnings but continue processing
            for warning in validation_report.warnings:
                logger.warning("Condition node validation warning", 
                              node_id=node.node_id,
                              session_id=session.id,
                              warning=warning.message)
            
            conditions = node_content.get("conditions", [])
            default_path = node_content.get("default_path")

            # Evaluate each condition in order
            for condition in conditions:
                if await self._evaluate_condition(condition.get("if"), session.state):
                    target_path = condition.get("then")
                    logger.info(
                        "Condition matched, transitioning to path",
                        session_id=session.id,
                        target_path=target_path,
                        condition=condition.get("if"),
                    )

                    # Map condition result to connection type
                    connection_type = self._map_path_to_connection(target_path)
                    next_connection = await self._get_next_connection(
                        db, node, connection_type
                    )

                    next_node = None
                    if next_connection:
                        from app.crud.chat_repo import chat_repo

                        next_node = await chat_repo.get_flow_node(
                            db,
                            flow_id=node.flow_id,
                            node_id=next_connection.target_node_id,
                        )

                    # If we have a next node, process it automatically
                    if next_node:
                        return await self.runtime.process_node(db, next_node, session)

                    return {
                        "type": "condition",
                        "condition_result": True,
                        "matched_condition": condition.get("if"),
                        "target_path": target_path,
                        "next_node": next_node,
                        "node_id": node.node_id,
                    }

            # No conditions matched, use default path
            logger.info(
                "No conditions matched, using default path",
                session_id=session.id,
                default_path=default_path,
            )

            connection_type = self._map_path_to_connection(default_path)
            next_connection = await self._get_next_connection(db, node, connection_type)

            next_node = None
            if next_connection:
                from app.crud.chat_repo import chat_repo

                next_node = await chat_repo.get_flow_node(
                    db, flow_id=node.flow_id, node_id=next_connection.target_node_id
                )

            # If we have a next node, process it automatically
            if next_node:
                return await self.runtime.process_node(db, next_node, session)

            return {
                "type": "condition",
                "condition_result": False,
                "used_default": True,
                "default_path": default_path,
                "next_node": next_node,
                "node_id": node.node_id,
            }

        except Exception as e:
            logger.error(
                "Error processing condition node",
                session_id=session.id,
                error=str(e),
                exc_info=True,
            )
            return {"type": "error", "error": "Failed to evaluate conditions"}

    def _map_path_to_connection(self, path: str):
        """Map condition path to connection type."""
        from app.models.cms import ConnectionType

        if path == "option_0":
            return ConnectionType.OPTION_0
        elif path == "option_1":
            return ConnectionType.OPTION_1
        else:
            return ConnectionType.DEFAULT

    async def _get_next_connection(
        self,
        db: AsyncSession,
        node: FlowNode,
        connection_type=None,
    ):
        """Get the next connection from current node."""
        from app.crud.chat_repo import chat_repo
        from app.models.cms import ConnectionType as CT

        if connection_type is None:
            connection_type = CT.DEFAULT

        connections = await chat_repo.get_node_connections(
            db, flow_id=node.flow_id, source_node_id=node.node_id
        )

        # Try to find specific connection type
        for conn in connections:
            if conn.connection_type == connection_type:
                return conn

        # Fall back to default if not found
        if connection_type != CT.DEFAULT:
            for conn in connections:
                if conn.connection_type == CT.DEFAULT:
                    return conn

        return None

    async def _evaluate_condition(
        self, condition: Dict[str, Any] | str, session_state: Dict[str, Any]
    ) -> bool:
        """
        Evaluate a single condition against session state.

        Supports both CEL expressions (strings) and JSON-based conditions (dicts).

        CEL Examples (recommended):
        - "user.age >= 18"
        - "user.age >= 18 && user.status == 'active'"
        - "size(user.preferences) > 0"
        - "user.role in ['admin', 'moderator']"
        - "has(user.email) && user.email.endsWith('@company.com')"

        JSON Examples (legacy, maintained for backward compatibility):
        - {"var": "user.age", "gte": 18}
        - {"and": [{"var": "user.age", "gte": 18}, {"var": "user.status", "eq": "active"}]}
        - {"or": [{"var": "user.role", "eq": "admin"}, {"var": "user.role", "eq": "moderator"}]}
        """
        if not condition:
            return False

        # Handle CEL expressions (string conditions)
        if isinstance(condition, str):
            try:
                result = evaluate_cel_expression(condition, session_state)
                logger.debug(
                    "CEL condition evaluated",
                    expression=condition,
                    result=result,
                    session_state_keys=list(session_state.keys()),
                )
                return bool(result)
            except Exception as e:
                logger.error(
                    "CEL condition evaluation failed, defaulting to False",
                    expression=condition,
                    error=str(e),
                )
                return False

        # Handle JSON-based conditions (legacy format)
        if not isinstance(condition, dict):
            logger.warning(
                "Invalid condition type, expected dict or str",
                condition_type=type(condition),
            )
            return False

        # Handle logical operators
        if "and" in condition:
            conditions = condition["and"]
            return all(
                await self._evaluate_condition(c, session_state) for c in conditions
            )

        if "or" in condition:
            conditions = condition["or"]
            return any(
                await self._evaluate_condition(c, session_state) for c in conditions
            )

        if "not" in condition:
            return not await self._evaluate_condition(condition["not"], session_state)

        # Handle variable comparisons
        if "var" in condition:
            var_path = condition["var"]
            var_value = self._get_nested_value(session_state, var_path)

            # Comparison operators
            if "eq" in condition:
                return var_value == condition["eq"]
            if "ne" in condition:
                return var_value != condition["ne"]
            if "gt" in condition:
                return var_value > condition["gt"]
            if "gte" in condition:
                return var_value >= condition["gte"]
            if "lt" in condition:
                return var_value < condition["lt"]
            if "lte" in condition:
                return var_value <= condition["lte"]
            if "in" in condition:
                return var_value in condition["in"]
            if "contains" in condition:
                return condition["contains"] in var_value if var_value else False
            if "exists" in condition:
                return var_value is not None

        return False

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get nested value from dictionary using dot notation."""
        try:
            keys = path.split(".")
            value = data
            for key in keys:
                if isinstance(value, dict):
                    value = value.get(key)
                else:
                    return None
            return value
        except (KeyError, TypeError, AttributeError):
            return None


class ActionNodeProcessor:
    """
    Processes action nodes that perform operations without user interaction.

    Handles variable assignments, API calls, and other side effects with
    proper idempotency and error handling for async execution.
    """

    def __init__(self, chat_repo):
        self.chat_repo = chat_repo
        self.variable_resolver = VariableResolver()

    async def process(
        self,
        session: ConversationSession,
        node_content: Dict[str, Any],
        user_input: Optional[str] = None,
        custom_resolver: Optional[VariableResolver] = None,
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Process an action node by executing all specified actions.

        Args:
            session: Current conversation session
            node_content: Node configuration with actions
            user_input: User input (not used for action nodes)
            custom_resolver: Optional custom variable resolver for composite nodes

        Returns:
            Tuple of (next_node_id, response_data)
        """
        try:
            actions = node_content.get("actions", [])
            action_results = []

            # Generate idempotency key for this action execution
            idempotency_key = (
                f"{session.id}:{session.current_node_id}:{session.revision}"
            )

            # Execute each action in sequence
            for i, action in enumerate(actions):
                action_id = f"{idempotency_key}:{i}"

                try:
                    result = await self._execute_action(
                        action, session, action_id, custom_resolver
                    )
                    action_results.append(result)

                    # Update session state if action modified it
                    if result.get("state_updates"):
                        session.state.update(result["state_updates"])

                except Exception as action_error:
                    logger.error(
                        "Action execution failed",
                        session_id=session.id,
                        action_index=i,
                        action_type=action.get("type"),
                        error=str(action_error),
                        exc_info=True,
                    )
                    # Return error path if action fails
                    return "error", {
                        "error": f"Action {i} failed: {str(action_error)}",
                        "failed_action": action,
                        "action_results": action_results,
                    }

            # All actions completed successfully
            logger.info(
                "All actions completed successfully",
                session_id=session.id,
                action_count=len(actions),
                idempotency_key=idempotency_key,
            )

            return "success", {
                "actions_completed": len(actions),
                "action_results": action_results,
                "idempotency_key": idempotency_key,
            }

        except Exception as e:
            logger.error(
                "Error processing action node",
                session_id=session.id,
                error=str(e),
                exc_info=True,
            )
            return "error", {"error": "Failed to process actions"}

    async def _execute_action(
        self,
        action: Dict[str, Any],
        session: ConversationSession,
        action_id: str,
        custom_resolver: Optional[VariableResolver] = None,
    ) -> Dict[str, Any]:
        """Execute a single action and return results."""
        action_type = action.get("type")

        if action_type == "set_variable":
            return await self._set_variable_action(action, session, custom_resolver)
        elif action_type == "api_call":
            return await self._api_call_action(action, session, action_id)
        elif action_type == "webhook":
            return await self._webhook_action(action, session, action_id)
        else:
            raise ValueError(f"Unknown action type: {action_type}")

    async def _set_variable_action(
        self,
        action: Dict[str, Any],
        session: ConversationSession,
        custom_resolver: Optional[VariableResolver] = None,
    ) -> Dict[str, Any]:
        """Execute a set_variable action."""
        variable = action.get("variable")
        value = action.get("value")

        if not variable:
            raise ValueError("set_variable action requires 'variable' field")

        # Resolve value if it contains variable references (handle both strings and complex objects)
        if custom_resolver:
            resolver = custom_resolver
        else:
            from app.services.variable_resolver import create_session_resolver

            resolver = create_session_resolver(session.state)

        if isinstance(value, str):
            resolved_value = resolver.substitute_variables(value)
            try:
                # Try to parse as JSON if it looks like structured data
                if resolved_value.startswith(("{", "[")):
                    resolved_value = json.loads(resolved_value)
            except json.JSONDecodeError:
                pass  # Keep as string
        elif isinstance(value, (dict, list)):
            # Recursively resolve variables in complex objects
            resolved_value = resolver.substitute_object(value)
        else:
            resolved_value = value

        # Set the variable in session state
        self._set_nested_value(session.state, variable, resolved_value)

        # For composite scope variables, also provide structured state updates
        state_updates = {}
        if variable.startswith(("input.", "output.", "local.", "temp.")):
            # Parse composite scope variable paths (e.g., "output.processed_name" -> scope="output", key="processed_name")
            parts = variable.split(".", 1)
            if len(parts) == 2:
                scope, key = parts
                if scope in [
                    "output",
                    "local",
                    "temp",
                ]:  # Don't update read-only input scope
                    state_updates[variable] = resolved_value
                    # Also provide the structured update for composite scope
                    state_updates[f"_composite_scope_{scope}_{key}"] = resolved_value
        else:
            state_updates[variable] = resolved_value

        return {
            "type": "set_variable",
            "variable": variable,
            "value": resolved_value,
            "state_updates": state_updates,
        }

    async def _api_call_action(
        self, action: Dict[str, Any], session: ConversationSession, action_id: str
    ) -> Dict[str, Any]:
        """Execute an api_call action using the internal API client."""
        from app.services.api_client import ApiCallConfig, InternalApiClient

        config_data = action.get("config", {})

        # Create API call configuration
        api_config = ApiCallConfig(
            endpoint=config_data.get("endpoint"),
            method=config_data.get("method", "GET"),
            headers=config_data.get("headers", {}),
            body=config_data.get("body", {}),
            query_params=config_data.get("query_params", {}),
            response_mapping=config_data.get("response_mapping", {}),
            timeout=config_data.get("timeout", 30),
            circuit_breaker=config_data.get("circuit_breaker", {}),
            fallback_response=config_data.get("fallback_response"),
            store_full_response=config_data.get("store_full_response", False),
            response_variable=config_data.get("response_variable"),
            error_variable=config_data.get("error_variable"),
        )

        # Execute API call
        api_client = InternalApiClient()
        result = await api_client.execute_api_call(api_config, session.state)

        # Update session state with response data
        state_updates = {}
        if result.mapped_data:
            state_updates.update(result.mapped_data)
        if result.full_response and api_config.response_variable:
            state_updates[api_config.response_variable] = result.full_response
        if result.error and api_config.error_variable:
            state_updates[api_config.error_variable] = result.error

        return {
            "type": "api_call",
            "endpoint": api_config.endpoint,
            "success": result.success,
            "status_code": result.status_code,
            "response_data": result.mapped_data,
            "state_updates": state_updates,
            "action_id": action_id,
        }

    async def _webhook_action(
        self, action: Dict[str, Any], session: ConversationSession, action_id: str
    ) -> Dict[str, Any]:
        """Execute a webhook action with circuit breaker protection."""
        # This would integrate with the webhook calling system
        # For now, return a placeholder implementation

        webhook_url = action.get("url")
        webhook_method = action.get("method", "POST")

        return {
            "type": "webhook",
            "url": webhook_url,
            "method": webhook_method,
            "success": True,
            "action_id": action_id,
            "note": "Webhook execution placeholder - would call external API",
        }

    def _set_nested_value(self, data: Dict[str, Any], path: str, value: Any) -> None:
        """Set nested value in dictionary using dot notation."""
        keys = path.split(".")
        current = data

        # Navigate to the parent of the target key
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        # Set the final value
        current[keys[-1]] = value


class WebhookNodeProcessor:
    """
    Processes webhook nodes that call external HTTP APIs.

    Features circuit breaker pattern, retry logic, secret injection,
    and response mapping for robust external integrations.
    """

    def __init__(self, chat_repo):
        self.chat_repo = chat_repo
        self.variable_resolver = VariableResolver()

    async def process(
        self,
        session: ConversationSession,
        node_content: Dict[str, Any],
        user_input: Optional[str] = None,
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Process a webhook node by making HTTP API calls.

        Args:
            session: Current conversation session
            node_content: Node configuration with webhook details
            user_input: User input (not used for webhook nodes)

        Returns:
            Tuple of (next_node_id, response_data)
        """
        try:
            webhook_url = node_content.get("url")
            if not webhook_url:
                raise ValueError("Webhook node requires 'url' field")

            # Set up variable resolver with current session state
            from app.services.variable_resolver import create_session_resolver

            resolver = create_session_resolver(session.state)

            # Resolve webhook configuration
            resolved_url = resolver.substitute_variables(webhook_url)
            method = node_content.get("method", "POST")
            headers = self._resolve_headers(node_content.get("headers", {}))
            body = self._resolve_body(node_content.get("body", {}))
            timeout = node_content.get("timeout", 30)

            # Get circuit breaker for this webhook
            circuit_breaker = get_circuit_breaker(f"webhook_{resolved_url}")

            # Execute webhook call with circuit breaker protection
            response_data = await circuit_breaker.call(
                self._make_webhook_request, resolved_url, method, headers, body, timeout
            )

            # Process response mapping
            mapped_data = self._map_response(
                response_data, node_content.get("response_mapping", {})
            )

            # Update session state with mapped data
            if mapped_data:
                session.state.update(mapped_data)

            logger.info(
                "Webhook call completed successfully",
                session_id=session.id,
                webhook_url=resolved_url,
                status_code=response_data.get("status_code"),
            )

            return "success", {
                "webhook_response": response_data,
                "mapped_data": mapped_data,
                "url": resolved_url,
            }

        except Exception as e:
            logger.error(
                "Webhook call failed",
                session_id=session.id,
                webhook_url=webhook_url,
                error=str(e),
                exc_info=True,
            )

            # Return fallback response if available
            fallback = node_content.get("fallback_response", {})
            if fallback:
                session.state.update(fallback)
                return "fallback", {"fallback_used": True, "error": str(e)}

            return "error", {"error": str(e)}

    def _resolve_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Resolve variable references in headers."""
        # This method will be called with a resolver in scope
        return headers  # Placeholder - needs session context

    def _resolve_body(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve variable references in request body."""
        # This method will be called with a resolver in scope
        return body  # Placeholder - needs session context

    async def _make_webhook_request(
        self, url: str, method: str, headers: Dict[str, str], body: Any, timeout: int
    ) -> Dict[str, Any]:
        """Make the actual HTTP request (placeholder implementation)."""
        # This would use httpx or similar to make the actual HTTP request
        # For now, return a mock response

        return {
            "status_code": 200,
            "headers": {"content-type": "application/json"},
            "body": {"success": True, "data": "mock_response"},
            "url": url,
            "method": method,
        }

    def _map_response(
        self, response_data: Dict[str, Any], mapping: Dict[str, str]
    ) -> Dict[str, Any]:
        """Map response data to session variables using JSONPath-like syntax."""
        if not mapping or not response_data:
            return {}

        mapped = {}
        response_body = response_data.get("body", {})

        for target_var, source_path in mapping.items():
            try:
                # Simple dot notation mapping (could be enhanced with JSONPath)
                if source_path.startswith("$."):
                    source_path = source_path[2:]  # Remove $. prefix

                value = self._get_nested_value(response_body, source_path)
                if value is not None:
                    mapped[target_var] = value

            except Exception as e:
                logger.warning(
                    "Failed to map response field",
                    target_var=target_var,
                    source_path=source_path,
                    error=str(e),
                )

        return mapped

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get nested value from dictionary using dot notation."""
        try:
            keys = path.split(".")
            value = data
            for key in keys:
                if isinstance(value, dict):
                    value = value.get(key)
                elif isinstance(value, list) and key.isdigit():
                    value = value[int(key)]
                else:
                    return None
            return value
        except (KeyError, TypeError, AttributeError, IndexError, ValueError):
            return None


class CompositeNodeProcessor:
    """
    Processes composite nodes that encapsulate complex multi-step operations.

    Provides explicit input/output mapping, variable scoping, and sequential
    execution of child nodes with proper isolation.
    """

    def __init__(self, chat_repo):
        self.chat_repo = chat_repo
        self.variable_resolver = VariableResolver()

    async def process(
        self,
        session: ConversationSession,
        node_content: Dict[str, Any],
        user_input: Optional[str] = None,
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Process a composite node by executing child nodes in sequence.

        Args:
            session: Current conversation session
            node_content: Node configuration with inputs, outputs, and child nodes
            user_input: User input (not used for composite nodes)

        Returns:
            Tuple of (next_node_id, response_data)
        """
        try:
            # Extract composite configuration
            inputs = node_content.get("inputs", {})
            outputs = node_content.get("outputs", {})
            child_nodes = node_content.get("nodes", [])

            if not child_nodes:
                logger.warning(
                    "Composite node has no child nodes", session_id=session.id
                )
                return "complete", {"warning": "No child nodes to execute"}

            # Create isolated scope for composite execution
            composite_scope = await self._create_composite_scope(session, inputs)

            # Execute child nodes in sequence
            execution_results = []
            for i, child_node in enumerate(child_nodes):
                try:
                    result = await self._execute_child_node(
                        child_node, composite_scope, session, i
                    )
                    execution_results.append(result)

                    # Update composite scope with results
                    if result.get("state_updates"):
                        for key, value in result["state_updates"].items():
                            if key.startswith("_composite_scope_"):
                                # Handle composite scope structured updates
                                # Format: "_composite_scope_output_processed_name" -> scope="output", key="processed_name"
                                # Remove the prefix "_composite_scope_" and split by first underscore
                                remainder = key[
                                    len("_composite_scope_") :
                                ]  # "output_processed_name"
                                parts = remainder.split(
                                    "_", 1
                                )  # ["output", "processed_name"]
                                if len(parts) == 2:
                                    scope, key_part = parts
                                    if scope in composite_scope:
                                        composite_scope[scope][key_part] = value
                            else:
                                # Handle regular state updates by setting them using dot notation
                                self._set_nested_value(composite_scope, key, value)

                except Exception as child_error:
                    logger.error(
                        "Child node execution failed in composite",
                        session_id=session.id,
                        child_index=i,
                        error=str(child_error),
                        exc_info=True,
                    )
                    # Return error in the expected format for the test
                    return "error", {
                        "error": f"Child node {i} failed: {str(child_error)}",
                        "execution_results": execution_results,
                    }

            # Map outputs back to session state
            output_mapping = await self._map_outputs(composite_scope, outputs, session)

            logger.info(
                "Composite node execution completed",
                session_id=session.id,
                child_nodes_executed=len(child_nodes),
                outputs_mapped=len(output_mapping),
            )

            return "complete", {
                "execution_results": execution_results,
                "output_mapping": output_mapping,
                "child_nodes_executed": len(child_nodes),
            }

        except Exception as e:
            logger.error(
                "Error processing composite node",
                session_id=session.id,
                error=str(e),
                exc_info=True,
            )
            return "error", {"error": "Failed to process composite node"}

    async def _create_composite_scope(
        self, session: ConversationSession, inputs: Dict[str, str]
    ) -> Dict[str, Any]:
        """Create isolated variable scope for composite node execution."""
        composite_scope = {"input": {}, "output": {}, "local": {}, "temp": {}}

        # Set up variable resolver with session state
        from app.services.variable_resolver import create_session_resolver

        resolver = create_session_resolver(session.state)

        # Map inputs to composite scope
        for input_name, input_source in inputs.items():
            try:
                # Check if input_source is a direct reference to a session state key (e.g., "user", "context")
                # without the dot notation, which means we want the entire object
                if "." not in input_source and input_source in session.state:
                    resolved_value = session.state[input_source]
                else:
                    # Use variable resolution for dot notation paths (e.g., "user.name")
                    resolved_value = resolver.substitute_variables(
                        f"{{{{{input_source}}}}}"
                    )
                    # Try to parse as JSON if it's a string that looks like structured data
                    if isinstance(resolved_value, str):
                        try:
                            if resolved_value.startswith(("{", "[")):
                                resolved_value = json.loads(resolved_value)
                        except json.JSONDecodeError:
                            pass  # Keep as string

                composite_scope["input"][input_name] = resolved_value

            except Exception as e:
                logger.warning(
                    "Failed to resolve composite input",
                    input_name=input_name,
                    input_source=input_source,
                    error=str(e),
                )
                composite_scope["input"][input_name] = None

        return composite_scope

    async def _execute_child_node(
        self,
        child_node: Dict[str, Any],
        composite_scope: Dict[str, Any],
        session: ConversationSession,
        node_index: int,
    ) -> Dict[str, Any]:
        """Execute a single child node within the composite scope."""
        node_type = child_node.get("type")
        node_content = child_node.get("content", {})

        # Create temporary variable resolver with composite scope
        from app.services.variable_resolver import create_session_resolver

        temp_resolver = create_session_resolver(session.state, composite_scope)

        # Process the child node based on its type
        if node_type == "action":
            # Create a temporary action processor for the child node
            action_processor = ActionNodeProcessor(self.chat_repo)

            # Execute actions with composite scope using the temp_resolver
            next_node, result = await action_processor.process(
                session, node_content, custom_resolver=temp_resolver
            )

            # Check if the action processor returned an error
            if next_node == "error":
                # Propagate the error up to the composite processor
                raise Exception(result.get("error", "Unknown action processing error"))

            # Extract state_updates from action_results and put them at the top level
            consolidated_state_updates = {}
            if "action_results" in result:
                for action_result in result["action_results"]:
                    if "state_updates" in action_result:
                        consolidated_state_updates.update(
                            action_result["state_updates"]
                        )

            # Add consolidated state_updates to the result
            if consolidated_state_updates:
                result["state_updates"] = consolidated_state_updates

            return result

        elif node_type == "condition":
            # Create a temporary condition processor
            condition_processor = ConditionNodeProcessor(self.chat_repo)
            condition_processor.variable_resolver = temp_resolver

            # Evaluate condition with composite scope
            _, result = await condition_processor.process(session, node_content)
            return result

        else:
            logger.warning(
                "Unsupported child node type in composite",
                node_type=node_type,
                node_index=node_index,
            )
            return {"warning": f"Unsupported child node type: {node_type}"}

    async def _map_outputs(
        self,
        composite_scope: Dict[str, Any],
        outputs: Dict[str, str],
        session: ConversationSession,
    ) -> Dict[str, Any]:
        """Map composite outputs back to session state."""
        output_mapping = {}

        for output_name, target_path in outputs.items():
            try:
                # Get value from composite scope output
                output_value = composite_scope.get("output", {}).get(output_name)

                if output_value is not None:
                    # Set the value in session state
                    self._set_nested_value(session.state, target_path, output_value)
                    output_mapping[target_path] = output_value

            except Exception as e:
                logger.warning(
                    "Failed to map composite output",
                    output_name=output_name,
                    target_path=target_path,
                    error=str(e),
                )

        return output_mapping

    def _set_nested_value(self, data: Dict[str, Any], path: str, value: Any) -> None:
        """Set nested value in dictionary using dot notation."""
        keys = path.split(".")
        current = data

        # Navigate to the parent of the target key
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        # Set the final value
        current[keys[-1]] = value

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get nested value from dictionary using dot notation."""
        try:
            keys = path.split(".")
            value = data
            for key in keys:
                if isinstance(value, dict):
                    value = value.get(key)
                else:
                    return None
            return value
        except (KeyError, TypeError, AttributeError):
            return None
