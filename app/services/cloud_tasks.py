"""Cloud Tasks integration for async node processing."""

import json
from typing import Any, Dict, Optional
from uuid import UUID

from google.cloud import tasks_v2
from structlog import get_logger

from app.config import get_settings
from app.crud.chat_repo import chat_repo

logger = get_logger()
settings = get_settings()


class CloudTasksService:
    """Service for managing Cloud Tasks queue operations."""

    def __init__(self):
        self.client = tasks_v2.CloudTasksClient()
        self.logger = logger

        # Cloud Tasks configuration
        self.project_id = settings.GCP_PROJECT_ID
        self.location = settings.GCP_LOCATION
        self.queue_name = settings.GCP_CLOUD_TASKS_NAME or "chatbot-async-nodes"

        # Full queue path
        self.queue_path = self.client.queue_path(
            self.project_id, self.location, self.queue_name
        )

    async def enqueue_action_task(
        self,
        session_id: UUID,
        node_id: str,
        session_revision: int,
        action_type: str,
        params: Dict[str, Any],
        delay_seconds: int = 0,
    ) -> str:
        """Enqueue an ACTION node processing task."""

        # Generate idempotency key
        idempotency_key = chat_repo.generate_idempotency_key(
            session_id, node_id, session_revision
        )

        # Prepare task payload
        task_payload = {
            "task_type": "action_node",
            "session_id": str(session_id),
            "node_id": node_id,
            "session_revision": session_revision,
            "idempotency_key": idempotency_key,
            "action_type": action_type,
            "params": params,
        }

        return await self._enqueue_task(
            task_payload, delay_seconds, idempotency_key, f"/internal/tasks/action-node"
        )

    async def enqueue_webhook_task(
        self,
        session_id: UUID,
        node_id: str,
        session_revision: int,
        webhook_config: Dict[str, Any],
        delay_seconds: int = 0,
    ) -> str:
        """Enqueue a WEBHOOK node processing task."""

        # Generate idempotency key
        idempotency_key = chat_repo.generate_idempotency_key(
            session_id, node_id, session_revision
        )

        # Prepare task payload
        task_payload = {
            "task_type": "webhook_node",
            "session_id": str(session_id),
            "node_id": node_id,
            "session_revision": session_revision,
            "idempotency_key": idempotency_key,
            "webhook_config": webhook_config,
        }

        return await self._enqueue_task(
            task_payload,
            delay_seconds,
            idempotency_key,
            f"/internal/tasks/webhook-node",
        )

    async def _enqueue_task(
        self,
        payload: Dict[str, Any],
        delay_seconds: int,
        idempotency_key: str,
        endpoint_path: str,
    ) -> str:
        """Enqueue a generic task to Cloud Tasks."""

        # Prepare the request
        task = {
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": f"{settings.WRIVETED_INTERNAL_API}{endpoint_path}",
                "headers": {
                    "Content-Type": "application/json",
                    "X-Idempotency-Key": idempotency_key,
                },
                "body": json.dumps(payload).encode(),
            }
        }

        # Add delay if specified
        if delay_seconds > 0:
            import datetime

            from google.protobuf import timestamp_pb2

            schedule_time = datetime.datetime.utcnow() + datetime.timedelta(
                seconds=delay_seconds
            )
            timestamp = timestamp_pb2.Timestamp()
            timestamp.FromDatetime(schedule_time)
            task["schedule_time"] = timestamp

        try:
            # Create the task
            response = self.client.create_task(
                request={"parent": self.queue_path, "task": task}
            )

            task_name = response.name
            self.logger.info(
                "Task enqueued successfully",
                task_name=task_name,
                idempotency_key=idempotency_key,
                endpoint_path=endpoint_path,
                delay_seconds=delay_seconds,
            )

            return task_name

        except Exception as e:
            self.logger.error(
                "Failed to enqueue task",
                error=str(e),
                idempotency_key=idempotency_key,
                endpoint_path=endpoint_path,
            )
            raise


# Create singleton instance
cloud_tasks = CloudTasksService()
