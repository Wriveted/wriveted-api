"""
Flow Webhook Service - Reliable webhook delivery for flow events via Event Outbox.

This service provides reliable webhook delivery for flow state changes by:
1. Looking up configured webhook subscriptions
2. Creating outbox entries for each subscription
3. Letting the outbox processor handle reliable delivery with retries

This replaces the unreliable NOTIFY-only approach with a durable, transactional pattern.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.models.event_outbox import EventOutbox, EventPriority
from app.models.webhook_subscription import (
    WebhookSubscription,
    WebhookSubscriptionStatus,
)
from app.services.event_listener import FlowEvent
from app.services.event_outbox_service import EventOutboxService

logger = get_logger()


class FlowWebhookService:
    """
    Service for publishing flow events to webhooks via the Event Outbox.

    This provides reliable, transactional webhook delivery that:
    - Survives application restarts
    - Handles transient failures with retries
    - Supports multiple webhook subscriptions per flow
    - Integrates with the circuit breaker pattern
    """

    def __init__(self, outbox_service: Optional[EventOutboxService] = None):
        self.outbox_service = outbox_service or EventOutboxService()

    async def publish_flow_event(
        self,
        db: AsyncSession,
        event: FlowEvent,
    ) -> List[EventOutbox]:
        """
        Publish a flow event to all matching webhook subscriptions.

        Creates an outbox entry for each matching subscription, ensuring
        reliable delivery even if the application crashes.

        Args:
            db: Database session (same transaction as the triggering operation)
            event: The flow event to publish

        Returns:
            List of created outbox entries
        """
        # Find matching webhook subscriptions
        subscriptions = await self._get_matching_subscriptions(
            db,
            event_type=event.event_type,
            flow_id=event.flow_id,
        )

        if not subscriptions:
            logger.debug(
                "No webhook subscriptions for event",
                event_type=event.event_type,
                flow_id=event.flow_id,
            )
            return []

        # Create outbox entries for each subscription
        outbox_entries = []
        for subscription in subscriptions:
            entry = await self._create_webhook_outbox_entry(
                db,
                subscription=subscription,
                event=event,
            )
            outbox_entries.append(entry)

        logger.info(
            "Published flow event to webhook outbox",
            event_type=event.event_type,
            flow_id=event.flow_id,
            session_id=event.session_id,
            subscription_count=len(outbox_entries),
        )

        return outbox_entries

    async def publish_flow_event_from_dict(
        self,
        db: AsyncSession,
        event_type: str,
        session_id: uuid.UUID,
        flow_id: uuid.UUID,
        *,
        user_id: Optional[uuid.UUID] = None,
        current_node: Optional[str] = None,
        previous_node: Optional[str] = None,
        status: Optional[str] = None,
        previous_status: Optional[str] = None,
        revision: Optional[int] = None,
        previous_revision: Optional[int] = None,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> List[EventOutbox]:
        """
        Publish a flow event from individual parameters.

        Convenience method for cases where a FlowEvent object isn't available.
        """
        event = FlowEvent(
            event_type=event_type,
            session_id=session_id,
            flow_id=flow_id,
            timestamp=datetime.utcnow().timestamp(),
            user_id=user_id,
            current_node=current_node,
            previous_node=previous_node,
            status=status,
            previous_status=previous_status,
            revision=revision,
            previous_revision=previous_revision,
        )

        return await self.publish_flow_event(db, event)

    async def _get_matching_subscriptions(
        self,
        db: AsyncSession,
        event_type: str,
        flow_id: uuid.UUID,
    ) -> List[WebhookSubscription]:
        """Get all active webhook subscriptions matching the event."""
        # Query for active subscriptions that:
        # 1. Are active status
        # 2. Match the flow_id (or are global with null flow_id)
        # 3. Match the event type (or subscribe to all events with empty list)
        query = (
            select(WebhookSubscription)
            .where(WebhookSubscription.status == WebhookSubscriptionStatus.ACTIVE)
            .where(
                (WebhookSubscription.flow_id.is_(None))
                | (WebhookSubscription.flow_id == flow_id)
            )
        )

        result = await db.execute(query)
        subscriptions = result.scalars().all()

        # Filter by event type (done in Python since JSONB array contains is complex)
        matching = [
            sub for sub in subscriptions if sub.matches_event(event_type, flow_id)
        ]

        return matching

    async def _create_webhook_outbox_entry(
        self,
        db: AsyncSession,
        subscription: WebhookSubscription,
        event: FlowEvent,
    ) -> EventOutbox:
        """Create an outbox entry for a webhook subscription."""
        # Build the webhook payload
        payload = {
            "event_type": event.event_type,
            "timestamp": event.timestamp,
            "session_id": str(event.session_id),
            "flow_id": str(event.flow_id),
            "user_id": str(event.user_id) if event.user_id else None,
            "data": {
                "current_node": event.current_node,
                "previous_node": event.previous_node,
                "status": event.status,
                "previous_status": event.previous_status,
                "revision": event.revision,
                "previous_revision": event.previous_revision,
            },
        }

        # Build headers including secret for HMAC
        headers = dict(subscription.headers or {})
        if subscription.secret:
            headers["secret"] = subscription.secret
        if subscription.timeout_seconds:
            headers["timeout_seconds"] = str(subscription.timeout_seconds)

        # Create outbox entry
        return await self.outbox_service.publish_event(
            db,
            event_type=f"flow_webhook:{event.event_type}",
            destination=f"webhook:{subscription.url}",
            payload=payload,
            priority=EventPriority.NORMAL,
            headers=headers if headers else None,
            max_retries=subscription.max_retries,
            correlation_id=f"{event.session_id}:{event.event_type}",
            user_id=event.user_id,
            session_id=event.session_id,
            flow_id=event.flow_id,
        )


# Global service instance
_flow_webhook_service: Optional[FlowWebhookService] = None


def get_flow_webhook_service() -> FlowWebhookService:
    """Get the global flow webhook service instance."""
    global _flow_webhook_service
    if _flow_webhook_service is None:
        _flow_webhook_service = FlowWebhookService()
    return _flow_webhook_service


def reset_flow_webhook_service() -> None:
    """Reset the global service instance (for testing)."""
    global _flow_webhook_service
    _flow_webhook_service = None


async def flow_event_outbox_handler(
    db: AsyncSession,
    event: FlowEvent,
) -> None:
    """
    Handler function to publish flow events to webhook outbox.

    This can be called from database triggers or application code to ensure
    flow events are reliably delivered to webhooks.
    """
    service = get_flow_webhook_service()
    await service.publish_flow_event(db, event)
