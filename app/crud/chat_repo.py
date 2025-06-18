import base64
import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from structlog import get_logger

from app.models.cms import (
    ConversationHistory,
    ConversationSession,
    FlowConnection,
    FlowNode,
    InteractionType,
    SessionStatus,
)

logger = get_logger()


class ChatRepository:
    """Repository for chat-related database operations with concurrency support."""

    def __init__(self):
        self.logger = logger

    async def get_session_by_token(
        self, db: AsyncSession, session_token: str
    ) -> Optional[ConversationSession]:
        """Get session by token with eager loading of relationships."""
        result = await db.scalars(
            select(ConversationSession)
            .where(ConversationSession.session_token == session_token)
            .options(
                selectinload(ConversationSession.flow),
                selectinload(ConversationSession.user),
            )
        )
        return result.first()

    async def create_session(
        self,
        db: AsyncSession,
        *,
        flow_id: UUID,
        user_id: Optional[UUID] = None,
        session_token: str,
        initial_state: Optional[Dict[str, Any]] = None,
        meta_data: Optional[Dict[str, Any]] = None,
    ) -> ConversationSession:
        """Create a new conversation session with initial state."""
        state = initial_state or {}
        state_hash = self._calculate_state_hash(state)

        session = ConversationSession(
            flow_id=flow_id,
            user_id=user_id,
            session_token=session_token,
            state=state,
            info=meta_data or {},
            status=SessionStatus.ACTIVE,
            revision=1,
            state_hash=state_hash,
        )

        db.add(session)
        await db.commit()
        await db.refresh(session)

        return session

    async def update_session_state(
        self,
        db: AsyncSession,
        *,
        session_id: UUID,
        state_updates: Dict[str, Any],
        current_node_id: Optional[str] = None,
        expected_revision: Optional[int] = None,
    ) -> ConversationSession:
        """Update session state with optimistic concurrency control."""
        # Get current session
        result = await db.scalars(
            select(ConversationSession)
            .where(ConversationSession.id == session_id)
            .with_for_update()  # Lock the row
        )
        session = result.first()

        if not session:
            raise ValueError("Session not found")

        # Check revision if provided (optimistic locking)
        if expected_revision is not None and session.revision != expected_revision:
            raise IntegrityError(
                "Session state has been modified by another process",
                params=None,
                orig=ValueError("Concurrent modification detected"),
            )

        # Update state
        current_state = session.state or {}
        current_state.update(state_updates)

        # Calculate new state hash
        new_state_hash = self._calculate_state_hash(current_state)

        # Update session
        session.state = current_state
        session.state_hash = new_state_hash
        session.revision = session.revision + 1
        session.last_activity_at = datetime.utcnow()

        if current_node_id:
            session.current_node_id = current_node_id

        await db.commit()
        await db.refresh(session)

        return session

    async def end_session(
        self,
        db: AsyncSession,
        *,
        session_id: UUID,
        status: SessionStatus = SessionStatus.COMPLETED,
    ) -> ConversationSession:
        """End a conversation session."""
        result = await db.scalars(
            select(ConversationSession).where(ConversationSession.id == session_id)
        )
        session = result.first()

        if not session:
            raise ValueError("Session not found")

        session.status = status
        session.ended_at = datetime.utcnow()
        session.last_activity_at = datetime.utcnow()

        await db.commit()
        await db.refresh(session)

        return session

    async def add_interaction_history(
        self,
        db: AsyncSession,
        *,
        session_id: UUID,
        node_id: str,
        interaction_type: InteractionType,
        content: Dict[str, Any],
    ) -> ConversationHistory:
        """Add an interaction to the conversation history."""
        history_entry = ConversationHistory(
            session_id=session_id,
            node_id=node_id,
            interaction_type=interaction_type,
            content=content,
        )

        db.add(history_entry)
        await db.commit()
        await db.refresh(history_entry)

        return history_entry

    async def get_session_history(
        self, db: AsyncSession, *, session_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[ConversationHistory]:
        """Get conversation history for a session."""
        result = await db.scalars(
            select(ConversationHistory)
            .where(ConversationHistory.session_id == session_id)
            .order_by(ConversationHistory.created_at)
            .offset(skip)
            .limit(limit)
        )
        return result.all()

    async def get_flow_node(
        self, db: AsyncSession, *, flow_id: UUID, node_id: str
    ) -> Optional[FlowNode]:
        """Get a specific flow node."""
        result = await db.scalars(
            select(FlowNode).where(
                and_(FlowNode.flow_id == flow_id, FlowNode.node_id == node_id)
            )
        )
        return result.first()

    async def get_node_connections(
        self, db: AsyncSession, *, flow_id: UUID, source_node_id: str
    ) -> List[FlowConnection]:
        """Get all connections from a specific node."""
        result = await db.scalars(
            select(FlowConnection)
            .where(
                and_(
                    FlowConnection.flow_id == flow_id,
                    FlowConnection.source_node_id == source_node_id,
                )
            )
            .order_by(FlowConnection.connection_type)
        )
        return result.all()

    async def get_active_sessions_count(
        self,
        db: AsyncSession,
        *,
        flow_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
    ) -> int:
        """Get count of active sessions with optional filters."""
        query = select(func.count(ConversationSession.id)).where(
            ConversationSession.status == SessionStatus.ACTIVE
        )

        if flow_id:
            query = query.where(ConversationSession.flow_id == flow_id)

        if user_id:
            query = query.where(ConversationSession.user_id == user_id)

        result = await db.scalar(query)
        return result or 0

    async def cleanup_abandoned_sessions(
        self, db: AsyncSession, *, inactive_hours: int = 24
    ) -> int:
        """Mark inactive sessions as abandoned."""
        cutoff_time = datetime.utcnow() - timedelta(hours=inactive_hours)

        # Update sessions that haven't had activity
        result = await db.execute(
            update(ConversationSession)
            .where(
                and_(
                    ConversationSession.status == SessionStatus.ACTIVE,
                    ConversationSession.last_activity_at < cutoff_time,
                )
            )
            .values(status=SessionStatus.ABANDONED, ended_at=datetime.utcnow())
        )

        await db.commit()
        return result.rowcount

    def _calculate_state_hash(self, state: Dict[str, Any]) -> str:
        """Calculate SHA-256 hash of session state for integrity checking."""
        state_json = json.dumps(state, sort_keys=True, separators=(",", ":"))
        hash_bytes = hashlib.sha256(state_json.encode("utf-8")).digest()
        return base64.b64encode(hash_bytes).decode("ascii")  # 44 characters

    def generate_idempotency_key(
        self, session_id: UUID, node_id: str, revision: int
    ) -> str:
        """Generate idempotency key for async operations."""
        return f"{session_id}:{node_id}:{revision}"

    async def validate_task_revision(
        self, db: AsyncSession, session_id: UUID, expected_revision: int
    ) -> bool:
        """Validate that a task's revision matches current session revision."""
        result = await db.scalar(
            select(ConversationSession.revision).where(
                ConversationSession.id == session_id
            )
        )

        if result is None:
            self.logger.warning(
                "Session not found during revision validation", session_id=session_id
            )
            return False

        if result != expected_revision:
            self.logger.warning(
                "Task revision mismatch - discarding stale task",
                session_id=session_id,
                expected_revision=expected_revision,
                current_revision=result,
            )
            return False

        return True


# Create singleton instance
chat_repo = ChatRepository()
