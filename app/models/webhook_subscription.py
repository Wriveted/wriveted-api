"""
Webhook Subscription Model - Stores configured webhook endpoints for flow events.

This model stores webhook configurations that will receive flow event notifications
via the Event Outbox pattern for reliable delivery.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import UUID as SqlUUID
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.schemas import CaseInsensitiveStringEnum


class WebhookSubscriptionStatus(CaseInsensitiveStringEnum):
    """Status of webhook subscription."""

    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


class WebhookSubscription(Base):
    """
    Webhook Subscription - Stores webhook endpoint configurations.

    Webhooks are triggered for flow events and delivered reliably via the Event Outbox.

    Features:
    - Event type filtering (subscribe to specific events or all)
    - Flow-specific subscriptions (filter by flow_id)
    - HMAC signature verification support
    - Health tracking for circuit breaker pattern
    """

    __tablename__ = "webhook_subscriptions"

    id = Column(SqlUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Webhook endpoint configuration
    name = Column(String(255), nullable=False)
    url = Column(Text, nullable=False)
    secret = Column(String(255), nullable=True)  # For HMAC signature verification

    # Request configuration
    method = Column(String(10), nullable=False, default="POST")
    headers = Column(JSONB, nullable=True)  # Additional headers to send
    timeout_seconds = Column(Integer, nullable=False, default=30)
    max_retries = Column(Integer, nullable=False, default=3)

    # Event filtering
    event_types: Mapped[List[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )  # Empty list = all events

    # Optional flow-specific filtering
    flow_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("flow_definitions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Status and health
    status: Mapped[WebhookSubscriptionStatus] = mapped_column(
        Enum(WebhookSubscriptionStatus, name="webhooksubscriptionstatus"),
        nullable=False,
        default=WebhookSubscriptionStatus.ACTIVE,
        index=True,
    )

    # Health tracking for circuit breaker
    consecutive_failures = Column(Integer, nullable=False, default=0)
    last_success_at = Column(DateTime, nullable=True)
    last_failure_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)

    # Ownership
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    flow = relationship("FlowDefinition", lazy="select")

    def __repr__(self):
        return (
            f"<WebhookSubscription(id={self.id}, name='{self.name}', "
            f"url='{self.url[:50]}...', status='{self.status}')>"
        )

    def matches_event(
        self, event_type: str, flow_id: Optional[uuid.UUID] = None
    ) -> bool:
        """Check if this subscription should receive the given event."""
        if self.status != WebhookSubscriptionStatus.ACTIVE:
            return False

        # Check flow filter
        if self.flow_id is not None and flow_id != self.flow_id:
            return False

        # Check event type filter (empty list means all events)
        if self.event_types and event_type not in self.event_types:
            return False

        return True

    @property
    def is_healthy(self) -> bool:
        """Check if webhook is considered healthy based on recent failures."""
        # Circuit breaker: disable after 5 consecutive failures
        return self.consecutive_failures < 5

    def record_success(self) -> None:
        """Record a successful delivery."""
        self.consecutive_failures = 0
        self.last_success_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def record_failure(self, error: str) -> None:
        """Record a failed delivery."""
        self.consecutive_failures += 1
        self.last_failure_at = datetime.utcnow()
        self.last_error = error
        self.updated_at = datetime.utcnow()
