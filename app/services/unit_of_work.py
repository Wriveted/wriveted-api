"""
Unit of Work Pattern - Transaction boundary management for service layer.

This implements the Unit of Work pattern as defined in the architecture docs:
- Provides transaction boundaries for write operations
- Aggregates repository access under single transaction
- Enables atomic commits with domain events
- Supports both explicit and context manager usage
"""

from abc import ABC, abstractmethod
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.protocols import (
    ContentRepository,
    ConversationRepository,
    EventOutboxRepository,
    FlowRepository,
)


class UnitOfWork(ABC):
    """
    Abstract Unit of Work interface.

    Aggregates repositories under a single transaction boundary.
    Each repository operates on the same database session/transaction.
    """

    content_repo: ContentRepository
    flow_repo: FlowRepository
    conversation_repo: ConversationRepository
    outbox_repo: EventOutboxRepository

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            await self.commit()
        else:
            await self.rollback()

    @abstractmethod
    async def commit(self) -> None:
        """Commit the current transaction."""
        pass

    @abstractmethod
    async def rollback(self) -> None:
        """Rollback the current transaction."""
        pass


class SQLUnitOfWork(UnitOfWork):
    """
    SQLAlchemy implementation of Unit of Work pattern.

    Uses a single AsyncSession to provide transaction boundary across
    all repository operations. Repositories are lazy-loaded on first access.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self._transaction: Optional[object] = None

        # Repository instances will be created on-demand
        self._content_repo: Optional[ContentRepository] = None
        self._flow_repo: Optional[FlowRepository] = None
        self._conversation_repo: Optional[ConversationRepository] = None
        self._outbox_repo: Optional[EventOutboxRepository] = None

    async def __aenter__(self):
        # Begin transaction
        self._transaction = await self.session.begin()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            await self.commit()
        else:
            await self.rollback()

    @property
    def content_repo(self) -> ContentRepository:
        """Lazy-loaded content repository."""
        if self._content_repo is None:
            from app.repositories.cms_repository import CMSRepositoryImpl

            self._content_repo = CMSRepositoryImpl(self.session)
        return self._content_repo

    @property
    def flow_repo(self) -> FlowRepository:
        """Lazy-loaded flow repository."""
        if self._flow_repo is None:
            from app.repositories.flow_repository import FlowRepositoryImpl

            self._flow_repo = FlowRepositoryImpl(self.session)
        return self._flow_repo

    @property
    def conversation_repo(self) -> ConversationRepository:
        """Lazy-loaded conversation repository."""
        if self._conversation_repo is None:
            from app.repositories.conversation_repository import (
                ConversationRepositoryImpl,
            )

            self._conversation_repo = ConversationRepositoryImpl(self.session)
        return self._conversation_repo

    @property
    def outbox_repo(self) -> EventOutboxRepository:
        """Lazy-loaded event outbox repository."""
        if self._outbox_repo is None:
            from app.services.event_outbox_service import EventOutboxService

            self._outbox_repo = EventOutboxService()
        return self._outbox_repo

    async def commit(self):
        """Commit the current transaction."""
        if self._transaction:
            await self._transaction.commit()
            self._transaction = None

    async def rollback(self):
        """Rollback the current transaction."""
        if self._transaction:
            await self._transaction.rollback()
            self._transaction = None
