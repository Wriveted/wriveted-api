"""
Event Outbox Model - Reliable event storage for the Event Outbox Pattern.

This implements the Event Outbox Pattern to ensure reliable event delivery
even when external systems are down or experience issues.
"""

from datetime import datetime
from typing import Any, Dict
from uuid import uuid4

from sqlalchemy import UUID as SqlUUID
from sqlalchemy import Column, DateTime, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.schemas import CaseInsensitiveStringEnum


class EventStatus(CaseInsensitiveStringEnum):
    """Status of events in the outbox."""

    PENDING = "pending"
    PROCESSING = "processing"
    PUBLISHED = "published"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class EventPriority(CaseInsensitiveStringEnum):
    """Priority levels for event processing."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class EventOutbox(Base):
    """
    Event Outbox - Stores events for reliable delivery.

    This table stores events in the same transaction as business data,
    ensuring that events are never lost even if external systems fail.

    Features:
    - Transactional safety: Events saved with business data
    - Retry logic: Failed events can be retried
    - Backpressure handling: Priority-based processing
    - Dead letter queue: Events that consistently fail
    """

    __tablename__ = "event_outbox"

    id = Column(SqlUUID(as_uuid=True), primary_key=True, default=uuid4)

    # Event metadata
    event_type = Column(String(100), nullable=False, index=True)
    event_version = Column(String(20), nullable=False, default="1.0")
    source_service = Column(String(50), nullable=False, default="wriveted-api")

    # Event routing
    destination = Column(String(100), nullable=False)  # webhook_url, slack, email, etc.
    routing_key = Column(String(100), nullable=True, index=True)

    # Event content
    payload = Column(JSONB, nullable=False)
    headers = Column(JSONB, nullable=True)

    # Processing metadata
    status: Mapped[EventStatus] = mapped_column(
        Enum(EventStatus, name="eventoutboxstatus"),
        nullable=False,
        default=EventStatus.PENDING,
        index=True,
    )
    priority: Mapped[EventPriority] = mapped_column(
        Enum(EventPriority, name="eventoutboxpriority"),
        nullable=False,
        default=EventPriority.NORMAL,
        index=True,
    )

    # Retry handling
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    next_retry_at = Column(DateTime, nullable=True, index=True)

    # Error tracking
    last_error = Column(Text, nullable=True)
    error_details = Column(JSONB, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)
    processed_at = Column(DateTime, nullable=True)

    # Business context (for debugging and correlation)
    correlation_id = Column(String(100), nullable=True, index=True)
    causation_id = Column(String(100), nullable=True)
    user_id = Column(SqlUUID(as_uuid=True), nullable=True)
    session_id = Column(SqlUUID(as_uuid=True), nullable=True)
    flow_id = Column(SqlUUID(as_uuid=True), nullable=True)

    def __repr__(self):
        return (
            f"<EventOutbox(id={self.id}, event_type='{self.event_type}', "
            f"status='{self.status}', destination='{self.destination}')>"
        )

    @property
    def is_retryable(self) -> bool:
        """Check if this event can be retried."""
        retry_count = self.retry_count if self.retry_count is not None else 0
        max_retries = self.max_retries if self.max_retries is not None else 3
        return (
            self.status in [EventStatus.PENDING, EventStatus.FAILED]
            and retry_count < max_retries
        )

    @property
    def should_move_to_dead_letter(self) -> bool:
        """Check if this event should be moved to dead letter queue."""
        retry_count = self.retry_count if self.retry_count is not None else 0
        max_retries = self.max_retries if self.max_retries is not None else 3
        return retry_count > max_retries

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for processing."""
        return {
            "id": str(self.id),
            "event_type": self.event_type,
            "event_version": self.event_version,
            "source_service": self.source_service,
            "destination": self.destination,
            "routing_key": self.routing_key,
            "payload": self.payload,
            "headers": self.headers,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "user_id": str(self.user_id) if self.user_id else None,
            "session_id": str(self.session_id) if self.session_id else None,
            "flow_id": str(self.flow_id) if self.flow_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
