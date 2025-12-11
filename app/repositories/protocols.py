"""
Repository protocol interfaces for dependency injection and testing.

These Protocol classes define the contracts that repository implementations must follow.
They enable:
- Type-safe dependency injection
- Easy mocking in tests
- Decoupling from concrete implementations
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol
from uuid import UUID

from app.models.cms import (
    CMSContent,
    ConversationHistory,
    ConversationSession,
    FlowConnection,
    FlowDefinition,
    FlowNode,
)
from app.models.event_outbox import EventOutbox


class FlowRepository(Protocol):
    """Protocol for Flow repository operations."""

    async def get_by_id(self, flow_id: UUID) -> Optional[FlowDefinition]: ...

    async def create(self, flow: FlowDefinition) -> FlowDefinition: ...

    async def update(self, flow: FlowDefinition) -> FlowDefinition: ...

    async def delete(self, flow_id: UUID) -> bool: ...

    async def publish(self, flow_id: UUID) -> FlowDefinition: ...


class ContentRepository(Protocol):
    """Protocol for Content repository operations."""

    async def get_by_id(self, content_id: UUID) -> Optional[CMSContent]: ...

    async def create(self, content: CMSContent) -> CMSContent: ...

    async def update(self, content: CMSContent) -> CMSContent: ...

    async def delete(self, content_id: UUID) -> bool: ...

    async def search(
        self, query: str, content_type: Optional[str] = None, limit: int = 100
    ) -> List[CMSContent]: ...


class ConversationRepository(Protocol):
    """Protocol for Conversation repository operations."""

    async def get_session_by_token(
        self, session_token: str
    ) -> Optional[ConversationSession]: ...

    async def create_session(
        self,
        flow_id: UUID,
        user_id: Optional[UUID],
        session_token: str,
        initial_state: Optional[Dict[str, Any]] = None,
    ) -> ConversationSession: ...

    async def update_session_state(
        self,
        session_id: UUID,
        state_updates: Dict[str, Any],
        current_node_id: Optional[str] = None,
        expected_revision: Optional[int] = None,
    ) -> ConversationSession: ...

    async def end_session(
        self, session_id: UUID, status: str
    ) -> ConversationSession: ...

    async def add_interaction_history(
        self,
        session_id: UUID,
        node_id: str,
        interaction_type: str,
        content: Dict[str, Any],
    ) -> ConversationHistory: ...


class EventOutboxRepository(Protocol):
    """Protocol for Event Outbox repository operations."""

    async def add_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        destination: str = "flow_events",
        priority: str = "normal",
    ) -> EventOutbox: ...

    async def get_pending_events(self, limit: int = 100) -> List[EventOutbox]: ...

    async def mark_event_delivered(self, event_id: UUID) -> bool: ...

    async def mark_event_failed(self, event_id: UUID, error_message: str) -> bool: ...
