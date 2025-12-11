"""
Core node processing logic that can be shared between synchronous and asynchronous execution.

This module eliminates code duplication by providing a single source of truth for
node processing business logic that can be called from both:
1. Synchronous chat runtime (immediate execution)
2. Asynchronous Cloud Tasks (background execution)

Enhanced with rigorous input validation to prevent runtime errors from malformed configurations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.models.cms import ConversationSession, NodeType
from app.repositories.chat_repository import chat_repo
from app.services.node_input_validation import validate_node_input
from app.services.variable_resolver import VariableResolver

logger = get_logger()


class NodeProcessorCore:
    """
    Core node processing logic that can be shared across execution contexts.

    This class contains the pure business logic for node processing without
    being tied to a specific execution model (sync vs async, HTTP vs task queue).
    """

    def __init__(self):
        self.variable_resolver = VariableResolver()

    async def execute_action_operations(
        self,
        db: AsyncSession,
        session: ConversationSession,
        actions: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a list of action operations with rigorous input validation.

        This is the core business logic that was duplicated between
        ActionNodeProcessor and _execute_action in tasks.py.

        Enhanced with comprehensive validation to prevent runtime errors.
        """
        context = context or {}
        results = []

        # Validate actions structure before processing
        validation_report = validate_node_input(
            node_id=f"actions_{session.id}",
            node_type=NodeType.ACTION,
            node_content={"actions": actions},
        )

        if not validation_report.is_valid:
            error_messages = [r.message for r in validation_report.errors]
            logger.error(
                "Action validation failed", session_id=session.id, errors=error_messages
            )
            return {
                "actions_executed": 0,
                "results": [],
                "validation_errors": error_messages,
                "session_updated": False,
            }

        # Log validation warnings but continue processing
        for warning in validation_report.warnings:
            logger.warning(
                "Action validation warning",
                session_id=session.id,
                warning=warning.message,
            )

        for i, action in enumerate(actions):
            action_type = action.get("type")
            params = action.get(
                "params", action
            )  # Support both nested and flat structure

            logger.info(
                "Executing action",
                action_type=action_type,
                action_index=i,
                session_id=session.id,
            )

            try:
                # Validate individual action parameters
                if not self._validate_action_params(action_type, params):
                    result = {
                        "error": f"Invalid parameters for action type: {action_type}"
                    }
                elif action_type == "set_variable":
                    result = await self._set_variable(db, session, params)
                elif action_type == "increment":
                    result = await self._increment_variable(db, session, params)
                elif action_type == "append":
                    result = await self._append_to_list(db, session, params)
                elif action_type == "remove":
                    result = await self._remove_from_list(db, session, params)
                elif action_type == "clear":
                    result = await self._clear_variable(db, session, params)
                elif action_type == "calculate":
                    result = await self._calculate(db, session, params)
                elif action_type == "api_call":
                    result = await self._execute_api_call(db, session, params, context)
                else:
                    logger.warning("Unknown action type", action_type=action_type)
                    result = {"error": f"Unknown action type: {action_type}"}

                results.append(
                    {"action_type": action_type, "action_index": i, "result": result}
                )

            except Exception as e:
                logger.error(
                    "Action execution failed",
                    action_type=action_type,
                    action_index=i,
                    session_id=session.id,
                    error=str(e),
                )
                results.append(
                    {
                        "action_type": action_type,
                        "action_index": i,
                        "result": {"error": f"Execution failed: {str(e)}"},
                    }
                )

        return {
            "actions_executed": len(actions),
            "results": results,
            "session_updated": True,
        }

    async def execute_webhook_operation(
        self,
        db: AsyncSession,
        session: ConversationSession,
        webhook_config: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a webhook operation with rigorous input validation.

        This centralizes webhook execution logic that was duplicated between
        WebhookNodeProcessor and _execute_webhook in tasks.py.

        Enhanced with comprehensive validation to prevent runtime errors.
        """
        import httpx

        from app.services.variable_resolver import create_session_resolver

        context = context or {}

        # Validate webhook configuration before processing
        validation_report = validate_node_input(
            node_id=f"webhook_{session.id}",
            node_type=NodeType.WEBHOOK,
            node_content=webhook_config,
        )

        if not validation_report.is_valid:
            error_messages = [r.message for r in validation_report.errors]
            logger.error(
                "Webhook validation failed",
                session_id=session.id,
                errors=error_messages,
            )
            return {
                "webhook_executed": False,
                "validation_errors": error_messages,
                "error": f"Webhook validation failed: {'; '.join(error_messages)}",
            }

        # Log validation warnings but continue processing
        for warning in validation_report.warnings:
            logger.warning(
                "Webhook validation warning",
                session_id=session.id,
                warning=warning.message,
            )

        # Resolve variables in webhook config
        resolver = create_session_resolver(session.state or {}, context)

        try:
            url = resolver.substitute_variables(webhook_config.get("url", ""))
            method = webhook_config.get("method", "POST").upper()
            headers = webhook_config.get("headers", {})
            payload = webhook_config.get("payload", {})
            timeout = webhook_config.get("timeout", 30)

            # Additional runtime validation after variable resolution
            if not url:
                return {
                    "webhook_executed": False,
                    "error": "Webhook URL is empty after variable resolution",
                }

            if not url.startswith(("http://", "https://")):
                return {
                    "webhook_executed": False,
                    "error": f"Invalid webhook URL protocol: {url}",
                }

            # Resolve variables in headers and payload
            resolved_headers = {
                k: resolver.substitute_variables(str(v)) for k, v in headers.items()
            }
            resolved_payload = resolver.substitute_object(payload) if payload else None

            logger.info(
                "Executing webhook",
                url=url,
                method=method,
                timeout=timeout,
                session_id=session.id,
            )

        except Exception as e:
            logger.error(
                "Webhook configuration resolution failed",
                session_id=session.id,
                error=str(e),
            )
            return {
                "webhook_executed": False,
                "error": f"Configuration resolution failed: {str(e)}",
            }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=resolved_headers,
                    json=resolved_payload,
                )

                response.raise_for_status()

                # Store webhook response in session state if configured
                if webhook_config.get("store_response"):
                    response_key = webhook_config.get(
                        "response_key", "webhook_response"
                    )
                    state_updates = {
                        "webhook_responses": {
                            response_key: {
                                "status_code": response.status_code,
                                "response": response.json()
                                if response.headers.get("content-type", "").startswith(
                                    "application/json"
                                )
                                else response.text,
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        }
                    }

                    await chat_repo.update_session_state(
                        db,
                        session_id=session.id,
                        state_updates=state_updates,
                        expected_revision=session.revision,
                    )

                return {
                    "webhook_executed": True,
                    "status_code": response.status_code,
                    "response_stored": webhook_config.get("store_response", False),
                }

        except Exception as e:
            logger.error(
                "Webhook execution failed", url=url, error=str(e), session_id=session.id
            )
            return {"webhook_executed": False, "error": str(e)}

    # Private helper methods for action execution

    async def _set_variable(
        self, db: AsyncSession, session: ConversationSession, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Set a variable in session state."""
        variable_name = params.get("variable")
        value = params.get("value")

        if not variable_name:
            return {"error": "Variable name is required"}

        # Handle scoped variables (e.g., "temp.counter")
        if "." in variable_name:
            scope, var_key = variable_name.split(".", 1)
            state_updates = {scope: {var_key: value}}
        else:
            state_updates = {"variables": {variable_name: value}}

        await chat_repo.update_session_state(
            db,
            session_id=session.id,
            state_updates=state_updates,
            expected_revision=session.revision,
        )

        return {"variable_set": variable_name, "value": value}

    async def _increment_variable(
        self, db: AsyncSession, session: ConversationSession, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Increment a numeric variable."""
        variable_name = params.get("variable")
        increment = params.get("increment", 1)

        if not variable_name:
            return {"error": "Variable name is required"}

        # Get current value
        current_value = 0
        if "." in variable_name:
            scope, var_key = variable_name.split(".", 1)
            current_value = session.state.get(scope, {}).get(var_key, 0)
            state_updates = {scope: {var_key: current_value + increment}}
        else:
            current_value = session.state.get("variables", {}).get(variable_name, 0)
            state_updates = {"variables": {variable_name: current_value + increment}}

        await chat_repo.update_session_state(
            db,
            session_id=session.id,
            state_updates=state_updates,
            expected_revision=session.revision,
        )

        return {
            "variable_incremented": variable_name,
            "new_value": current_value + increment,
        }

    async def _append_to_list(
        self, db: AsyncSession, session: ConversationSession, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Append to a list variable."""
        variable_name = params.get("variable")
        value = params.get("value")

        if not variable_name:
            return {"error": "Variable name is required"}

        # Get current list
        if "." in variable_name:
            scope, var_key = variable_name.split(".", 1)
            current_list = session.state.get(scope, {}).get(var_key, [])
            if not isinstance(current_list, list):
                current_list = []
            current_list.append(value)
            state_updates = {scope: {var_key: current_list}}
        else:
            current_list = session.state.get("variables", {}).get(variable_name, [])
            if not isinstance(current_list, list):
                current_list = []
            current_list.append(value)
            state_updates = {"variables": {variable_name: current_list}}

        await chat_repo.update_session_state(
            db,
            session_id=session.id,
            state_updates=state_updates,
            expected_revision=session.revision,
        )

        return {"value_appended": variable_name, "new_length": len(current_list)}

    async def _remove_from_list(
        self, db: AsyncSession, session: ConversationSession, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Remove from a list variable."""
        variable_name = params.get("variable")
        value = params.get("value")

        if not variable_name:
            return {"error": "Variable name is required"}

        # Get current list
        if "." in variable_name:
            scope, var_key = variable_name.split(".", 1)
            current_list = session.state.get(scope, {}).get(var_key, [])
            if isinstance(current_list, list) and value in current_list:
                current_list.remove(value)
            state_updates = {scope: {var_key: current_list}}
        else:
            current_list = session.state.get("variables", {}).get(variable_name, [])
            if isinstance(current_list, list) and value in current_list:
                current_list.remove(value)
            state_updates = {"variables": {variable_name: current_list}}

        await chat_repo.update_session_state(
            db,
            session_id=session.id,
            state_updates=state_updates,
            expected_revision=session.revision,
        )

        return {"value_removed": variable_name, "new_length": len(current_list)}

    async def _clear_variable(
        self, db: AsyncSession, session: ConversationSession, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Clear a variable (set to None)."""
        variable_name = params.get("variable")

        if not variable_name:
            return {"error": "Variable name is required"}

        if "." in variable_name:
            scope, var_key = variable_name.split(".", 1)
            state_updates = {scope: {var_key: None}}
        else:
            state_updates = {"variables": {variable_name: None}}

        await chat_repo.update_session_state(
            db,
            session_id=session.id,
            state_updates=state_updates,
            expected_revision=session.revision,
        )

        return {"variable_cleared": variable_name}

    async def _calculate(
        self, db: AsyncSession, session: ConversationSession, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform calculation and store result."""
        expression = params.get("expression")
        result_variable = params.get("result_variable")

        if not expression or not result_variable:
            return {"error": "Expression and result_variable are required"}

        try:
            # Use the variable resolver to evaluate the expression
            resolver = VariableResolver()
            resolver.set_scope("temp", session.state.get("temp", {}))
            resolver.set_scope("user", session.state.get("user", {}))
            resolver.set_scope("context", session.state.get("context", {}))
            resolved_expression = resolver.substitute_variables(expression)

            # Simple calculation evaluation (in production, use a safe evaluator)
            result = eval(resolved_expression)  # WARNING: Use safe eval in production

            # Store result
            if "." in result_variable:
                scope, var_key = result_variable.split(".", 1)
                state_updates = {scope: {var_key: result}}
            else:
                state_updates = {"variables": {result_variable: result}}

            await chat_repo.update_session_state(
                db,
                session_id=session.id,
                state_updates=state_updates,
                expected_revision=session.revision,
            )

            return {"calculation_result": result, "stored_in": result_variable}

        except Exception as e:
            logger.error("Calculation failed", expression=expression, error=str(e))
            return {"error": f"Calculation failed: {str(e)}"}

    async def _execute_api_call(
        self,
        db: AsyncSession,
        session: ConversationSession,
        params: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute an API call action."""
        import httpx

        from app.services.variable_resolver import create_session_resolver

        url = params.get("url")
        method = params.get("method", "GET").upper()
        headers = params.get("headers", {})
        payload = params.get("payload", {})
        store_response = params.get("store_response", False)
        response_key = params.get("response_key", "api_response")

        if not url:
            return {"error": "URL is required for API call"}

        # Resolve variables in API call configuration
        resolver = create_session_resolver(session.state or {}, context)
        resolved_url = resolver.substitute_variables(url)
        resolved_headers = {
            k: resolver.substitute_variables(str(v)) for k, v in headers.items()
        }
        resolved_payload = resolver.substitute_object(payload)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(
                    method=method,
                    url=resolved_url,
                    headers=resolved_headers,
                    json=resolved_payload
                    if method in ["POST", "PUT", "PATCH"]
                    else None,
                )

                response.raise_for_status()

                result = {
                    "api_call_executed": True,
                    "status_code": response.status_code,
                    "url": resolved_url,
                }

                # Store API response in session state if requested
                if store_response:
                    response_data = (
                        response.json()
                        if response.headers.get("content-type", "").startswith(
                            "application/json"
                        )
                        else response.text
                    )

                    state_updates = {
                        "api_responses": {
                            response_key: {
                                "status_code": response.status_code,
                                "data": response_data,
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        }
                    }

                    await chat_repo.update_session_state(
                        db,
                        session_id=session.id,
                        state_updates=state_updates,
                        expected_revision=session.revision,
                    )

                    result["response_stored"] = True
                    result["response_key"] = response_key

                return result

        except Exception as e:
            logger.error(
                "API call failed", url=resolved_url, method=method, error=str(e)
            )
            return {"api_call_executed": False, "error": str(e), "url": resolved_url}

    def _validate_action_params(self, action_type: str, params: Dict[str, Any]) -> bool:
        """
        Validate parameters for specific action types.

        Args:
            action_type: Type of action to validate
            params: Action parameters to validate

        Returns:
            True if parameters are valid, False otherwise
        """
        try:
            if action_type == "set_variable":
                return "variable" in params and "value" in params
            elif action_type == "increment":
                return "variable" in params
            elif action_type in ["append", "remove"]:
                return "variable" in params and "value" in params
            elif action_type == "clear":
                return "variable" in params
            elif action_type == "calculate":
                return "expression" in params and "result_variable" in params
            elif action_type == "api_call":
                return "url" in params
            else:
                # Unknown action type - let the main validation handle it
                return True
        except Exception as e:
            logger.error(
                "Parameter validation error", action_type=action_type, error=str(e)
            )
            return False


# Singleton instance for shared use
node_processor_core = NodeProcessorCore()
