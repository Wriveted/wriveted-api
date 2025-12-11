"""Internal API endpoints for Cloud Tasks processing."""

from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from structlog import get_logger

from app.api.dependencies.async_db_dep import DBSessionDep
from app.repositories.chat_repository import chat_repo
from app.services.node_processor_core import node_processor_core
from app.services.task_handler_decorator import (
    build_action_result_data,
    build_webhook_result_data,
    idempotent_task_handler,
)

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


async def _action_core_logic(
    payload: ActionNodeTaskPayload,
    session: DBSessionDep,
    current_session: Any,
    session_id: UUID,
    x_idempotency_key: str,
) -> Dict[str, Any]:
    """Core business logic for action node processing."""

    # Use shared core logic instead of duplicated implementation
    if payload.action_type == "composite":
        # Multiple actions
        actions = payload.params.get("actions", [])
        await node_processor_core.execute_action_operations(
            session, current_session, actions
        )
    else:
        # Single action
        action = {"type": payload.action_type, "params": payload.params}
        await node_processor_core.execute_action_operations(
            session, current_session, [action]
        )

    return {
        "idempotency_key": x_idempotency_key,
        "action_type": payload.action_type,
    }


@router.post("/action-node")
@idempotent_task_handler(
    task_type="Action node",
    success_log_message="Action node task completed",
    error_log_message="Action node task failed",
    core_logic_func=_action_core_logic,
    result_data_builder=build_action_result_data,
)
async def process_action_node_task(
    payload: ActionNodeTaskPayload,
    session: DBSessionDep,
    x_idempotency_key: str = Header(alias="X-Idempotency-Key"),
) -> Dict[str, Any]:
    """Process an ACTION node task from Cloud Tasks with database idempotency."""
    pass  # All logic handled by decorator


async def _webhook_core_logic(
    payload: WebhookNodeTaskPayload,
    session: DBSessionDep,
    current_session: Any,
    session_id: UUID,
    x_idempotency_key: str,
) -> Dict[str, Any]:
    """Core business logic for webhook node processing."""

    # Use shared core logic instead of duplicated implementation
    result = await node_processor_core.execute_webhook_operation(
        session, current_session, payload.webhook_config
    )

    return {
        "idempotency_key": x_idempotency_key,
        "webhook_result": result,
    }


@router.post("/webhook-node")
@idempotent_task_handler(
    task_type="Webhook node",
    success_log_message="Webhook node task completed",
    error_log_message="Webhook node task failed",
    core_logic_func=_webhook_core_logic,
    result_data_builder=build_webhook_result_data,
)
async def process_webhook_node_task(
    payload: WebhookNodeTaskPayload,
    session: DBSessionDep,
    x_idempotency_key: str = Header(alias="X-Idempotency-Key"),
) -> Dict[str, Any]:
    """Process a WEBHOOK node task from Cloud Tasks with database idempotency."""
    pass  # All logic handled by decorator
