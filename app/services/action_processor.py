"""
Action node processor with api_call action type implementation.

Handles ACTION nodes with various action types including:
- set_variable: Set session variables
- increment/decrement: Numeric operations
- api_call: Internal API calls with authentication
- delete_variable: Remove variables
"""

from datetime import datetime
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.models.cms import (
    ConnectionType,
    ConversationSession,
    FlowNode,
    InteractionType,
)
from app.repositories.chat_repository import chat_repo
from app.services.api_client import ApiCallConfig, get_api_client
from app.services.chat_runtime import NodeProcessor
from app.services.cloud_tasks import cloud_tasks

logger = get_logger()


class ActionNodeProcessor(NodeProcessor):
    """Processor for ACTION nodes with support for api_call actions."""

    async def process(
        self,
        db: AsyncSession,
        node: FlowNode,
        session: ConversationSession,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Process an action node."""
        node_content = node.content or {}
        actions = node_content.get("actions", [])

        # Determine if this should be processed asynchronously
        async_actions = {"api_call", "external_service", "heavy_computation"}
        should_async = any(
            action.get("type") in async_actions or action.get("async", False)
            for action in actions
        )

        if should_async:
            # Enqueue task for async processing
            try:
                task_name = await cloud_tasks.enqueue_action_task(
                    session_id=session.id,
                    node_id=node.node_id,
                    session_revision=session.revision,
                    action_type="composite",
                    params={"actions": actions},
                )

                logger.info(
                    "Action task enqueued",
                    task_name=task_name,
                    session_id=session.id,
                    node_id=node.node_id,
                    actions=len(actions),
                )

                # For async actions, return immediately and let the task continue flow
                return {
                    "type": "action",
                    "async": True,
                    "task_name": task_name,
                    "actions_count": len(actions),
                    "session_ended": False,
                }

            except Exception as e:
                logger.error(
                    "Failed to enqueue action task",
                    error=str(e),
                    session_id=session.id,
                    node_id=node.node_id,
                )
                # Fallback to synchronous processing

        # Process synchronously
        result = await self._execute_actions_sync(
            db, session, actions, node.node_id, context
        )

        # Get next connection
        connection_type = (
            ConnectionType.SUCCESS if result["success"] else ConnectionType.FAILURE
        )
        next_connection = await self.get_next_connection(db, node, connection_type)

        # Fall back to default if specific connection not found
        if not next_connection:
            next_connection = await self.get_next_connection(
                db, node, ConnectionType.DEFAULT
            )

        if next_connection:
            next_node = await chat_repo.get_flow_node(
                db, flow_id=node.flow_id, node_id=next_connection.target_node_id
            )
            if next_node:
                return await self.runtime.process_node(db, next_node, session, context)

        return {
            "type": "action",
            "success": result["success"],
            "variables": result["variables"],
            "errors": result["errors"],
            "session_ended": not next_connection,
        }

    async def _execute_actions_sync(
        self,
        db: AsyncSession,
        session: ConversationSession,
        actions: list,
        node_id: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute actions synchronously."""
        variables_updated = {}
        errors = []
        success = True

        current_state = session.state or {}

        for i, action in enumerate(actions):
            action_type = action.get("type")
            action_id = f"{node_id}_action_{i}"

            try:
                if action_type == "set_variable":
                    await self._handle_set_variable(
                        action, current_state, variables_updated
                    )

                elif action_type == "increment":
                    await self._handle_increment(
                        action, current_state, variables_updated
                    )

                elif action_type == "decrement":
                    await self._handle_decrement(
                        action, current_state, variables_updated
                    )

                elif action_type == "delete_variable":
                    await self._handle_delete_variable(
                        action, current_state, variables_updated
                    )

                elif action_type == "api_call":
                    await self._handle_api_call(
                        action, current_state, variables_updated, context
                    )

                else:
                    logger.warning(f"Unknown action type: {action_type}")
                    errors.append(f"Unknown action type: {action_type}")

            except Exception as e:
                error_msg = f"Action {action_id} failed: {str(e)}"
                logger.error(
                    "Action execution error", action_id=action_id, error=str(e)
                )
                errors.append(error_msg)
                success = False

        # Update session state if variables were modified
        if variables_updated:
            current_state.update(variables_updated)
            await chat_repo.update_session_state(
                db, session.id, current_state, session.revision + 1
            )

        # Record action execution in history
        await chat_repo.add_interaction_history(
            db,
            session_id=session.id,
            node_id=node_id,
            interaction_type=InteractionType.ACTION,
            content={
                "type": "action_execution",
                "actions_count": len(actions),
                "variables_updated": list(variables_updated.keys()),
                "success": success,
                "errors": errors,
                "timestamp": datetime.utcnow().isoformat(),
                "processed_async": False,
            },
        )

        return {
            "success": success and len(errors) == 0,
            "variables": variables_updated,
            "errors": errors,
        }

    async def _handle_set_variable(
        self, action: Dict[str, Any], state: Dict[str, Any], updates: Dict[str, Any]
    ) -> None:
        """Handle set_variable action."""
        variable = action.get("variable")
        value = action.get("value")

        if variable and value is not None:
            # Substitute variables in value if it's a string
            if isinstance(value, str):
                value = self.runtime.substitute_variables(value, state)

            self._set_nested_value(updates, variable, value)
            logger.debug(f"Set variable {variable} = {value}")

    async def _handle_increment(
        self, action: Dict[str, Any], state: Dict[str, Any], updates: Dict[str, Any]
    ) -> None:
        """Handle increment action."""
        variable = action.get("variable")
        amount = action.get("amount", 1)

        if variable:
            current = self._get_nested_value(state, variable) or 0
            new_value = current + amount
            self._set_nested_value(updates, variable, new_value)
            logger.debug(f"Incremented {variable}: {current} + {amount} = {new_value}")

    async def _handle_decrement(
        self, action: Dict[str, Any], state: Dict[str, Any], updates: Dict[str, Any]
    ) -> None:
        """Handle decrement action."""
        variable = action.get("variable")
        amount = action.get("amount", 1)

        if variable:
            current = self._get_nested_value(state, variable) or 0
            new_value = current - amount
            self._set_nested_value(updates, variable, new_value)
            logger.debug(f"Decremented {variable}: {current} - {amount} = {new_value}")

    async def _handle_delete_variable(
        self, action: Dict[str, Any], state: Dict[str, Any], updates: Dict[str, Any]
    ) -> None:
        """Handle delete_variable action."""
        variable = action.get("variable")

        if variable:
            self._set_nested_value(updates, variable, None)
            logger.debug(f"Deleted variable {variable}")

    async def _handle_api_call(
        self,
        action: Dict[str, Any],
        state: Dict[str, Any],
        updates: Dict[str, Any],
        context: Dict[str, Any],
    ) -> None:
        """Handle api_call action."""
        api_config_data = action.get("config", {})

        # Create API call configuration
        api_config = ApiCallConfig(**api_config_data)

        # Get composite scopes from context if available
        composite_scopes = context.get("composite_scopes")

        # Execute API call
        api_client = get_api_client()
        result = await api_client.execute_api_call(api_config, state, composite_scopes)

        if result.success:
            # Update variables with API response
            updates.update(result.variables_updated)
            logger.info(
                "API call successful",
                endpoint=api_config.endpoint,
                variables_updated=list(result.variables_updated.keys()),
            )
        else:
            # Store error information
            error_var = api_config_data.get("error_variable", "api_error")
            updates[error_var] = {
                "error": result.error_message,
                "status_code": result.status_code,
                "timestamp": datetime.utcnow().isoformat(),
                "fallback_used": result.fallback_used,
            }
            logger.error(
                "API call failed",
                endpoint=api_config.endpoint,
                error=result.error_message,
            )

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

    def _set_nested_value(
        self, data: Dict[str, Any], key_path: str, value: Any
    ) -> None:
        """Set nested value in dictionary using dot notation."""
        keys = key_path.split(".")
        current = data

        # Navigate to parent of target key
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        # Set the final value
        current[keys[-1]] = value
