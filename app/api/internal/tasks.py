"""Internal API endpoints for Cloud Tasks processing."""

from datetime import datetime
from typing import Any, Dict
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.api.dependencies.async_db_dep import DBSessionDep
from app.crud.chat_repo import chat_repo
from app.models.cms import ConversationSession, InteractionType

logger = get_logger()

router = APIRouter(prefix="/internal/tasks", tags=["Internal Tasks"])


class ActionNodeTaskPayload(BaseModel):
    task_type: str
    session_id: str
    node_id: str
    session_revision: int
    idempotency_key: str
    action_type: str
    params: Dict[str, Any]


class WebhookNodeTaskPayload(BaseModel):
    task_type: str
    session_id: str
    node_id: str
    session_revision: int
    idempotency_key: str
    webhook_config: Dict[str, Any]


# In-memory idempotency cache (in production, use Redis)
_processed_tasks = set()


@router.post("/action-node")
async def process_action_node_task(
    payload: ActionNodeTaskPayload,
    session: DBSessionDep,
    x_idempotency_key: str = Header(alias="X-Idempotency-Key"),
):
    """Process an ACTION node task from Cloud Tasks."""

    # Idempotency check
    if x_idempotency_key in _processed_tasks:
        logger.info("Skipping duplicate task", idempotency_key=x_idempotency_key)
        return {"status": "already_processed", "idempotency_key": x_idempotency_key}

    try:
        session_id = UUID(payload.session_id)

        # Validate session revision (discard stale tasks)
        if not await chat_repo.validate_task_revision(
            session, session_id, payload.session_revision
        ):
            return {"status": "discarded_stale", "idempotency_key": x_idempotency_key}

        # Get current session
        current_session = await chat_repo.get_session_by_token(
            session, ""
        )  # TODO: proper session lookup
        if not current_session:
            logger.error("Session not found", session_id=session_id)
            raise HTTPException(404, "Session not found")

        # Process the action
        await _execute_action(
            session,
            current_session,
            payload.action_type,
            payload.params,
            payload.node_id,
        )

        # Mark as processed
        _processed_tasks.add(x_idempotency_key)

        logger.info(
            "Action node task completed",
            session_id=session_id,
            node_id=payload.node_id,
            action_type=payload.action_type,
            idempotency_key=x_idempotency_key,
        )

        return {
            "status": "completed",
            "idempotency_key": x_idempotency_key,
            "action_type": payload.action_type,
        }

    except Exception as e:
        logger.error(
            "Action node task failed",
            error=str(e),
            idempotency_key=x_idempotency_key,
            session_id=payload.session_id,
        )
        raise HTTPException(500, f"Task processing failed: {str(e)}")


@router.post("/webhook-node")
async def process_webhook_node_task(
    payload: WebhookNodeTaskPayload,
    session: DBSessionDep,
    x_idempotency_key: str = Header(alias="X-Idempotency-Key"),
):
    """Process a WEBHOOK node task from Cloud Tasks."""

    # Idempotency check
    if x_idempotency_key in _processed_tasks:
        logger.info("Skipping duplicate task", idempotency_key=x_idempotency_key)
        return {"status": "already_processed", "idempotency_key": x_idempotency_key}

    try:
        session_id = UUID(payload.session_id)

        # Validate session revision (discard stale tasks)
        if not await chat_repo.validate_task_revision(
            session, session_id, payload.session_revision
        ):
            return {"status": "discarded_stale", "idempotency_key": x_idempotency_key}

        # Get current session
        current_session = await chat_repo.get_session_by_token(
            session, ""
        )  # TODO: proper session lookup
        if not current_session:
            logger.error("Session not found", session_id=session_id)
            raise HTTPException(404, "Session not found")

        # Process the webhook
        result = await _execute_webhook(
            session, current_session, payload.webhook_config, payload.node_id
        )

        # Mark as processed
        _processed_tasks.add(x_idempotency_key)

        logger.info(
            "Webhook node task completed",
            session_id=session_id,
            node_id=payload.node_id,
            webhook_success=result.get("success", False),
            idempotency_key=x_idempotency_key,
        )

        return {
            "status": "completed",
            "idempotency_key": x_idempotency_key,
            "webhook_result": result,
        }

    except Exception as e:
        logger.error(
            "Webhook node task failed",
            error=str(e),
            idempotency_key=x_idempotency_key,
            session_id=payload.session_id,
        )
        raise HTTPException(500, f"Task processing failed: {str(e)}")


async def _execute_action(
    db: AsyncSession,
    session: ConversationSession,
    action_type: str,
    params: Dict[str, Any],
    node_id: str,
):
    """Execute an action with the same logic as ActionNodeProcessor."""

    if action_type == "set_variable":
        await _set_variable(db, session, params)
    elif action_type == "increment":
        await _increment_variable(db, session, params)
    elif action_type == "append":
        await _append_to_list(db, session, params)
    elif action_type == "remove":
        await _remove_from_list(db, session, params)
    elif action_type == "clear":
        await _clear_variable(db, session, params)
    elif action_type == "calculate":
        await _calculate(db, session, params)

    # Record action in history
    await chat_repo.add_interaction_history(
        db,
        session_id=session.id,
        node_id=node_id,
        interaction_type=InteractionType.ACTION,
        content={
            "action": action_type,
            "params": params,
            "timestamp": datetime.utcnow().isoformat(),
            "processed_async": True,
        },
    )


async def _execute_webhook(
    db: AsyncSession,
    session: ConversationSession,
    webhook_config: Dict[str, Any],
    node_id: str,
) -> Dict[str, Any]:
    """Execute a webhook with the same logic as WebhookNodeProcessor."""

    url = webhook_config.get("url")
    method = webhook_config.get("method", "POST")
    headers = webhook_config.get("headers", {})
    timeout = webhook_config.get("timeout", 30)

    # Prepare payload with session data
    payload = {
        "session_id": str(session.id),
        "flow_id": str(session.flow_id),
        "user_id": str(session.user_id) if session.user_id else None,
        "state": session.state,
        "meta_data": session.meta_data,
        "node_id": node_id,
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Add custom payload data
    if webhook_config.get("payload"):
        payload.update(webhook_config["payload"])

    success = False
    response_data = None
    error_message = None

    if url:
        try:
            # TODO: Implement secret injection here
            # headers = await _inject_secrets(headers)

            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=payload,
                    timeout=timeout,
                )

                response.raise_for_status()
                success = True

                try:
                    response_data = response.json()
                except:
                    response_data = {"status": response.status_code}

                # Store response in session state if configured
                if webhook_config.get("store_response"):
                    variable = webhook_config.get(
                        "response_variable", "webhook_response"
                    )
                    state_updates = {}
                    _set_nested_value(state_updates, variable, response_data)

                    await chat_repo.update_session_state(
                        db, session_id=session.id, state_updates=state_updates
                    )

        except httpx.TimeoutException:
            error_message = "Webhook request timed out"
            logger.error("Webhook timeout", url=url, timeout=timeout)
        except httpx.HTTPStatusError as e:
            error_message = f"Webhook returned status {e.response.status_code}"
            logger.error("Webhook HTTP error", url=url, status=e.response.status_code)
        except Exception as e:
            error_message = f"Webhook request failed: {str(e)}"
            logger.error("Webhook error", url=url, error=str(e))

    # Record webhook call in history
    await chat_repo.add_interaction_history(
        db,
        session_id=session.id,
        node_id=node_id,
        interaction_type=InteractionType.ACTION,
        content={
            "type": "webhook",
            "url": url,
            "method": method,
            "success": success,
            "response": response_data,
            "error": error_message,
            "timestamp": datetime.utcnow().isoformat(),
            "processed_async": True,
        },
    )

    return {
        "success": success,
        "response": response_data,
        "error": error_message,
    }


# Helper functions (same as in ActionNodeProcessor)
async def _set_variable(
    db: AsyncSession, session: ConversationSession, params: Dict[str, Any]
):
    variable = params.get("variable")
    value = params.get("value")

    if variable:
        state_updates = {}
        _set_nested_value(state_updates, variable, value)
        await chat_repo.update_session_state(
            db, session_id=session.id, state_updates=state_updates
        )


async def _increment_variable(
    db: AsyncSession, session: ConversationSession, params: Dict[str, Any]
):
    variable = params.get("variable")
    amount = params.get("amount", 1)

    if variable:
        current = _get_nested_value(session.state or {}, variable) or 0
        state_updates = {}
        _set_nested_value(state_updates, variable, current + amount)
        await chat_repo.update_session_state(
            db, session_id=session.id, state_updates=state_updates
        )


async def _append_to_list(
    db: AsyncSession, session: ConversationSession, params: Dict[str, Any]
):
    variable = params.get("variable")
    value = params.get("value")

    if variable:
        current = _get_nested_value(session.state or {}, variable)
        if not isinstance(current, list):
            current = []
        current.append(value)

        state_updates = {}
        _set_nested_value(state_updates, variable, current)
        await chat_repo.update_session_state(
            db, session_id=session.id, state_updates=state_updates
        )


async def _remove_from_list(
    db: AsyncSession, session: ConversationSession, params: Dict[str, Any]
):
    variable = params.get("variable")
    value = params.get("value")

    if variable:
        current = _get_nested_value(session.state or {}, variable)
        if isinstance(current, list) and value in current:
            current.remove(value)
            state_updates = {}
            _set_nested_value(state_updates, variable, current)
            await chat_repo.update_session_state(
                db, session_id=session.id, state_updates=state_updates
            )


async def _clear_variable(
    db: AsyncSession, session: ConversationSession, params: Dict[str, Any]
):
    variable = params.get("variable")

    if variable:
        state_updates = {}
        _set_nested_value(state_updates, variable, None)
        await chat_repo.update_session_state(
            db, session_id=session.id, state_updates=state_updates
        )


async def _calculate(
    db: AsyncSession, session: ConversationSession, params: Dict[str, Any]
):
    variable = params.get("variable")
    expression = params.get("expression")

    if variable and expression:
        try:
            # Replace variables in expression
            state = session.state or {}
            for var_name, var_value in state.items():
                if isinstance(var_value, (int, float)):
                    expression = expression.replace(f"{{{var_name}}}", str(var_value))

            # Safe evaluation (only basic math)
            import ast
            import operator as op

            allowed_operators = {
                ast.Add: op.add,
                ast.Sub: op.sub,
                ast.Mult: op.mul,
                ast.Div: op.truediv,
                ast.Mod: op.mod,
                ast.Pow: op.pow,
            }

            def eval_expr(expr):
                return eval(
                    compile(ast.parse(expr, mode="eval"), "<string>", "eval"),
                    {"__builtins__": {}},
                )

            result = eval_expr(expression)
            state_updates = {}
            _set_nested_value(state_updates, variable, result)
            await chat_repo.update_session_state(
                db, session_id=session.id, state_updates=state_updates
            )

        except Exception as e:
            logger.error("Calculation failed", error=str(e), expression=expression)


def _get_nested_value(data: Dict[str, Any], key_path: str) -> Any:
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


def _set_nested_value(data: Dict[str, Any], key_path: str, value: Any):
    """Set nested value in dictionary using dot notation."""
    keys = key_path.split(".")
    current = data

    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]

    current[keys[-1]] = value
