"""Internal API endpoints for Cloud Tasks processing."""

from datetime import datetime
from typing import Any, Dict
from uuid import UUID

import httpx
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.api.dependencies.async_db_dep import DBSessionDep
from app.crud.chat_repo import chat_repo
from app.models.cms import ConversationSession, InteractionType
from app.services.cel_evaluator import evaluate_cel_expression

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


@router.post("/action-node")
async def process_action_node_task(
    payload: ActionNodeTaskPayload,
    session: DBSessionDep,
    x_idempotency_key: str = Header(alias="X-Idempotency-Key"),
) -> Dict[str, Any]:
    """Process an ACTION node task from Cloud Tasks with database idempotency."""

    try:
        session_id = UUID(payload.session_id)

        acquired, existing_result = await chat_repo.acquire_idempotency_lock(
            session,
            idempotency_key=x_idempotency_key,
            session_id=session_id,
            node_id=payload.node_id,
            session_revision=payload.session_revision,
        )

        if not acquired:
            logger.info(
                "Task already processed",
                idempotency_key=x_idempotency_key,
                existing_status=existing_result.get("status")
                if existing_result
                else None,
            )
            return existing_result or {}

        current_session = await chat_repo.get_session_by_id(session, session_id)
        if not current_session:
            await chat_repo.complete_idempotency_record(
                session,
                x_idempotency_key,
                success=True,
                result_data={
                    "status": "discarded_session_not_found",
                    "reason": "Session was deleted",
                },
            )

            logger.info(
                "Session not found - likely deleted, discarding task",
                session_id=session_id,
                idempotency_key=x_idempotency_key,
            )

            return {
                "status": "discarded_session_not_found",
                "idempotency_key": x_idempotency_key,
            }

        if not await chat_repo.validate_task_revision(
            session, session_id, payload.session_revision
        ):
            await chat_repo.complete_idempotency_record(
                session,
                x_idempotency_key,
                success=True,
                result_data={
                    "status": "discarded_stale",
                    "reason": "Task revision is stale",
                },
            )
            return {"status": "discarded_stale", "idempotency_key": x_idempotency_key}

        await _execute_action(
            session,
            current_session,
            payload.action_type,
            payload.params,
            payload.node_id,
        )

        result_data = {
            "status": "completed",
            "idempotency_key": x_idempotency_key,
            "action_type": payload.action_type,
        }

        await chat_repo.complete_idempotency_record(
            session, x_idempotency_key, success=True, result_data=result_data
        )

        logger.info(
            "Action node task completed",
            session_id=session_id,
            node_id=payload.node_id,
            action_type=payload.action_type,
            idempotency_key=x_idempotency_key,
        )

        return result_data

    except Exception as e:
        await chat_repo.complete_idempotency_record(
            session, x_idempotency_key, success=False, error_message=str(e)
        )

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
) -> Dict[str, Any]:
    """Process a WEBHOOK node task from Cloud Tasks with database idempotency."""

    try:
        session_id = UUID(payload.session_id)

        acquired, existing_result = await chat_repo.acquire_idempotency_lock(
            session,
            idempotency_key=x_idempotency_key,
            session_id=session_id,
            node_id=payload.node_id,
            session_revision=payload.session_revision,
        )

        if not acquired:
            logger.info(
                "Task already processed",
                idempotency_key=x_idempotency_key,
                existing_status=existing_result.get("status")
                if existing_result
                else None,
                existing_result=existing_result,
            )
            if existing_result is None:
                logger.error("DEBUG: existing_result is None, returning empty dict")
                return {
                    "error": "existing_result_is_none",
                    "idempotency_key": x_idempotency_key,
                }
            return existing_result

        current_session = await chat_repo.get_session_by_id(session, session_id)
        if not current_session:
            await chat_repo.complete_idempotency_record(
                session,
                x_idempotency_key,
                success=True,
                result_data={
                    "status": "discarded_session_not_found",
                    "reason": "Session was deleted",
                },
            )

            logger.info(
                "Session not found - likely deleted, discarding task",
                session_id=session_id,
                idempotency_key=x_idempotency_key,
            )

            return {
                "status": "discarded_session_not_found",
                "idempotency_key": x_idempotency_key,
            }

        if not await chat_repo.validate_task_revision(
            session, session_id, payload.session_revision
        ):
            await chat_repo.complete_idempotency_record(
                session,
                x_idempotency_key,
                success=True,
                result_data={
                    "status": "discarded_stale",
                    "reason": "Task revision is stale",
                },
            )
            return {"status": "discarded_stale", "idempotency_key": x_idempotency_key}

        result = await _execute_webhook(
            session, current_session, payload.webhook_config, payload.node_id
        )

        result_data = {
            "status": "completed",
            "idempotency_key": x_idempotency_key,
            "webhook_result": result,
        }

        await chat_repo.complete_idempotency_record(
            session, x_idempotency_key, success=True, result_data=result_data
        )

        logger.info(
            "Webhook node task completed",
            session_id=session_id,
            node_id=payload.node_id,
            webhook_success=result.get("success", False),
            idempotency_key=x_idempotency_key,
        )

        return result_data

    except Exception as e:
        await chat_repo.complete_idempotency_record(
            session, x_idempotency_key, success=False, error_message=str(e)
        )

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
) -> None:
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
        "info": session.info,
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
                except Exception:
                    response_data = {"status": response.status_code}

                # Store response in session state if configured
                if webhook_config.get("store_response"):
                    variable = webhook_config.get(
                        "response_variable", "webhook_response"
                    )
                    state_updates: Dict[str, Any] = {}
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
) -> None:
    variable = params.get("variable")
    value = params.get("value")

    if variable:
        state_updates: Dict[str, Any] = {}
        _set_nested_value(state_updates, variable, value)
        await chat_repo.update_session_state(
            db, session_id=session.id, state_updates=state_updates
        )


async def _increment_variable(
    db: AsyncSession, session: ConversationSession, params: Dict[str, Any]
) -> None:
    variable = params.get("variable")
    amount = params.get("amount", 1)

    if variable:
        current = _get_nested_value(session.state or {}, variable) or 0
        state_updates: Dict[str, Any] = {}
        _set_nested_value(state_updates, variable, current + amount)
        await chat_repo.update_session_state(
            db, session_id=session.id, state_updates=state_updates
        )


async def _append_to_list(
    db: AsyncSession, session: ConversationSession, params: Dict[str, Any]
) -> None:
    variable = params.get("variable")
    value = params.get("value")

    if variable:
        current = _get_nested_value(session.state or {}, variable)
        if not isinstance(current, list):
            current = []
        current.append(value)

        state_updates: Dict[str, Any] = {}
        _set_nested_value(state_updates, variable, current)
        await chat_repo.update_session_state(
            db, session_id=session.id, state_updates=state_updates
        )


async def _remove_from_list(
    db: AsyncSession, session: ConversationSession, params: Dict[str, Any]
) -> None:
    variable = params.get("variable")
    value = params.get("value")

    if variable:
        current = _get_nested_value(session.state or {}, variable)
        if isinstance(current, list) and value in current:
            current.remove(value)
            state_updates: Dict[str, Any] = {}
            _set_nested_value(state_updates, variable, current)
            await chat_repo.update_session_state(
                db, session_id=session.id, state_updates=state_updates
            )


async def _clear_variable(
    db: AsyncSession, session: ConversationSession, params: Dict[str, Any]
) -> None:
    variable = params.get("variable")

    if variable:
        state_updates: Dict[str, Any] = {}
        _set_nested_value(state_updates, variable, None)
        await chat_repo.update_session_state(
            db, session_id=session.id, state_updates=state_updates
        )


async def _calculate(
    db: AsyncSession, session: ConversationSession, params: Dict[str, Any]
) -> None:
    variable = params.get("variable")
    expression = params.get("expression")

    if variable and expression:
        try:
            # Prepare context with session state variables
            state = session.state or {}
            context = {}

            # Only include numeric values for mathematical expressions
            for var_name, var_value in state.items():
                if isinstance(var_value, (int, float, bool)):
                    context[var_name] = var_value

            # Evaluate expression using CEL
            result = evaluate_cel_expression(expression, context)

            # Store result in session state
            state_updates: Dict[str, Any] = {}
            _set_nested_value(state_updates, variable, result)
            await chat_repo.update_session_state(
                db, session_id=session.id, state_updates=state_updates
            )

        except Exception as e:
            logger.error("Calculation failed", error=str(e), expression=expression)


def _get_nested_value(data: Dict[str, Any], key_path: str) -> Any:
    """Get nested value from dictionary using dot notation."""
    keys = key_path.split(".")
    value: Any = data

    try:
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value
    except (KeyError, TypeError):
        return None


def _set_nested_value(data: Dict[str, Any], key_path: str, value: Any) -> None:
    """Set nested value in dictionary using dot notation."""
    keys = key_path.split(".")
    current = data

    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]

    current[keys[-1]] = value
