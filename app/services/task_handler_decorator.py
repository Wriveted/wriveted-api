"""Idempotent task handler decorator for Cloud Tasks background processing."""

import functools
from typing import Any, Callable, Dict, Optional
from uuid import UUID

from fastapi import HTTPException
from structlog import get_logger

from app.repositories.chat_repository import chat_repo

logger = get_logger()


class TaskHandlerResult:
    """Result of task handler execution."""

    def __init__(self, status: str, data: Dict[str, Any], idempotency_key: str):
        self.status = status
        self.data = data
        self.idempotency_key = idempotency_key


def idempotent_task_handler(
    task_type: str,
    success_log_message: str,
    error_log_message: str,
    core_logic_func: Callable,
    result_data_builder: Optional[Callable[[Any], Dict[str, Any]]] = None,
):
    """
    Decorator for idempotent background task handlers.

    Handles common boilerplate:
    - Idempotency lock acquisition and checking
    - Session existence validation
    - Task revision validation
    - Error completion and logging
    - Success completion and logging

    Args:
        task_type: Type of task for logging (e.g., "Action node", "Webhook node")
        success_log_message: Log message for successful completion
        error_log_message: Log message for errors
        core_logic_func: Function containing the actual business logic
        result_data_builder: Optional function to build custom result data from core result
    """

    def decorator(core_handler: Callable):
        @functools.wraps(core_handler)
        async def wrapper(
            payload: Any, session: Any, x_idempotency_key: str, **kwargs
        ) -> Dict[str, Any]:
            try:
                # Phase 1: Session ID parsing and validation
                session_id = UUID(payload.session_id)

                # Phase 2: Idempotency lock acquisition
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
                        task_type=task_type,
                        idempotency_key=x_idempotency_key,
                        existing_status=existing_result.get("status")
                        if existing_result
                        else None,
                    )
                    return existing_result or {}

                # Phase 3: Session existence validation
                current_session = await chat_repo.get_session_by_id(session, session_id)
                if not current_session:
                    result_data = {
                        "status": "discarded_session_not_found",
                        "reason": "Session was deleted",
                    }

                    await chat_repo.complete_idempotency_record(
                        session,
                        x_idempotency_key,
                        success=True,
                        result_data=result_data,
                    )

                    logger.info(
                        "Session not found - likely deleted, discarding task",
                        task_type=task_type,
                        session_id=session_id,
                        idempotency_key=x_idempotency_key,
                    )

                    return {
                        "status": "discarded_session_not_found",
                        "idempotency_key": x_idempotency_key,
                    }

                # Phase 4: Task revision validation
                if not await chat_repo.validate_task_revision(
                    session, session_id, payload.session_revision
                ):
                    result_data = {
                        "status": "discarded_stale",
                        "reason": "Task revision is stale",
                    }

                    await chat_repo.complete_idempotency_record(
                        session,
                        x_idempotency_key,
                        success=True,
                        result_data=result_data,
                    )

                    logger.info(
                        "Task revision is stale, discarding task",
                        task_type=task_type,
                        session_id=session_id,
                        expected_revision=payload.session_revision,
                        idempotency_key=x_idempotency_key,
                    )

                    return {
                        "status": "discarded_stale",
                        "idempotency_key": x_idempotency_key,
                    }

                # Phase 5: Execute core business logic
                core_result = await core_logic_func(
                    payload=payload,
                    session=session,
                    current_session=current_session,
                    session_id=session_id,
                    x_idempotency_key=x_idempotency_key,
                )

                # Phase 6: Build success result data
                if result_data_builder:
                    result_data = result_data_builder(core_result)
                else:
                    result_data = {
                        "status": "completed",
                        "idempotency_key": x_idempotency_key,
                        "result": core_result,
                    }

                # Phase 7: Complete idempotency record
                await chat_repo.complete_idempotency_record(
                    session, x_idempotency_key, success=True, result_data=result_data
                )

                # Phase 8: Success logging
                logger.info(
                    success_log_message,
                    task_type=task_type,
                    session_id=session_id,
                    node_id=payload.node_id,
                    idempotency_key=x_idempotency_key,
                )

                return result_data

            except Exception as e:
                # Phase 9: Error handling and completion
                await chat_repo.complete_idempotency_record(
                    session, x_idempotency_key, success=False, error_message=str(e)
                )

                logger.error(
                    error_log_message,
                    task_type=task_type,
                    error=str(e),
                    idempotency_key=x_idempotency_key,
                    session_id=getattr(payload, "session_id", "unknown"),
                )

                raise HTTPException(500, f"Task processing failed: {str(e)}")

        return wrapper

    return decorator


def build_action_result_data(core_result: Dict[str, Any]) -> Dict[str, Any]:
    """Build result data for action node tasks."""
    return {
        "status": "completed",
        "idempotency_key": core_result.get("idempotency_key"),
        "action_type": core_result.get("action_type"),
    }


def build_webhook_result_data(core_result: Dict[str, Any]) -> Dict[str, Any]:
    """Build result data for webhook node tasks."""
    return {
        "status": "completed",
        "idempotency_key": core_result.get("idempotency_key"),
        "webhook_result": core_result.get("webhook_result"),
    }
