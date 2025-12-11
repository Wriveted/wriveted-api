from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from structlog import get_logger

from app.models.cms import (
    ConversationHistory,
    ConversationSession,
    InteractionType,
    SessionStatus,
)

logger = get_logger()


class ConversationRepository(ABC):
    """
    Domain repository interface for conversation management.

    This interface defines domain-focused methods rather than generic CRUD,
    making the business intent clear and the code more maintainable.
    """

    @abstractmethod
    async def get_active_session_by_token(
        self, db: AsyncSession, session_token: str
    ) -> Optional[ConversationSession]:
        """Get an active conversation session by its token."""
        pass

    @abstractmethod
    async def start_new_conversation(
        self,
        db: AsyncSession,
        flow_id: UUID,
        user_id: Optional[UUID],
        initial_state: dict,
    ) -> ConversationSession:
        """Start a new conversation session."""
        pass

    @abstractmethod
    async def update_session_state(
        self,
        db: AsyncSession,
        session: ConversationSession,
        new_state: dict,
        current_node_id: Optional[str] = None,
    ) -> ConversationSession:
        """Update session state with optimistic concurrency control."""
        pass

    @abstractmethod
    async def add_interaction_to_history(
        self,
        db: AsyncSession,
        session: ConversationSession,
        node_id: str,
        interaction_type: InteractionType,
        content: dict,
    ) -> ConversationHistory:
        """Add an interaction to the conversation history."""
        pass

    @abstractmethod
    async def end_conversation(
        self,
        db: AsyncSession,
        session: ConversationSession,
        status: SessionStatus = SessionStatus.COMPLETED,
    ) -> ConversationSession:
        """End a conversation session."""
        pass

    @abstractmethod
    async def get_conversation_history(
        self,
        db: AsyncSession,
        session: ConversationSession,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[ConversationHistory]:
        """Get conversation history for a session."""
        pass


class ConversationRepositoryImpl(ConversationRepository):
    """
    PostgreSQL implementation of ConversationRepository.

    This provides concrete implementation while maintaining the domain interface,
    allowing for easy testing and potential database switching.
    """

    async def get_active_session_by_token(
        self, db: AsyncSession, session_token: str
    ) -> Optional[ConversationSession]:
        """Get an active conversation session by its token."""
        query = (
            select(ConversationSession)
            .options(selectinload(ConversationSession.flow))
            .where(
                and_(
                    ConversationSession.session_token == session_token,
                    ConversationSession.status == SessionStatus.ACTIVE,
                )
            )
        )

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def start_new_conversation(
        self,
        db: AsyncSession,
        flow_id: UUID,
        user_id: Optional[UUID],
        initial_state: dict,
    ) -> ConversationSession:
        """Start a new conversation session."""
        import secrets

        session_token = secrets.token_urlsafe(32)

        new_session = ConversationSession(
            flow_id=flow_id,
            user_id=user_id,
            session_token=session_token,
            state=initial_state,
            status=SessionStatus.ACTIVE,
            started_at=datetime.utcnow(),
            last_activity_at=datetime.utcnow(),
        )

        db.add(new_session)
        await db.flush()  # Get the ID
        await db.refresh(new_session, ["flow"])

        logger.info(
            "Started new conversation",
            session_id=new_session.id,
            flow_id=flow_id,
            user_id=user_id,
        )

        return new_session

    async def update_session_state(
        self,
        db: AsyncSession,
        session: ConversationSession,
        new_state: dict,
        current_node_id: Optional[str] = None,
    ) -> ConversationSession:
        """Update session state with optimistic concurrency control."""
        # Simple update for now - full concurrency control in Phase 2
        session.state = new_state
        session.last_activity_at = datetime.utcnow()

        if current_node_id:
            session.current_node_id = current_node_id

        await db.flush()
        await db.refresh(session)

        logger.debug(
            "Updated session state", session_id=session.id, current_node=current_node_id
        )

        return session

    async def add_interaction_to_history(
        self,
        db: AsyncSession,
        session: ConversationSession,
        node_id: str,
        interaction_type: InteractionType,
        content: dict,
    ) -> ConversationHistory:
        """Add an interaction to the conversation history."""
        interaction = ConversationHistory(
            session_id=session.id,
            node_id=node_id,
            interaction_type=interaction_type,
            content=content,
            created_at=datetime.utcnow(),
        )

        db.add(interaction)
        await db.flush()

        logger.debug(
            "Added interaction to history",
            session_id=session.id,
            node_id=node_id,
            interaction_type=interaction_type.value,
        )

        return interaction

    async def end_conversation(
        self,
        db: AsyncSession,
        session: ConversationSession,
        status: SessionStatus = SessionStatus.COMPLETED,
    ) -> ConversationSession:
        """End a conversation session."""
        session.status = status
        session.ended_at = datetime.utcnow()
        session.last_activity_at = datetime.utcnow()

        await db.flush()
        await db.refresh(session)

        logger.info("Ended conversation", session_id=session.id, status=status.value)

        return session

    async def get_conversation_history(
        self,
        db: AsyncSession,
        session: ConversationSession,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[ConversationHistory]:
        """Get conversation history for a session."""
        query = (
            select(ConversationHistory)
            .where(ConversationHistory.session_id == session.id)
            .order_by(ConversationHistory.created_at)
        )

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        result = await db.execute(query)
        return result.scalars().all()
