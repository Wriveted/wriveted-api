"""
Concurrency Control Service - Prevents lost updates and ensures data consistency.

This service implements PostgreSQL advisory locks and revision control
to prevent lost updates from concurrent writers (user + background tasks).
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.models.cms import ConversationSession

logger = get_logger()


class ConcurrencyControlService:
    """
    Service for managing concurrency and preventing lost updates.

    This service addresses the architectural issue of concurrent session updates
    by providing:
    - Advisory locks per session for exclusive access
    - Revision control to detect concurrent modifications
    - Clear conflict resolution (user interactions win over background tasks)
    """

    def __init__(self):
        self.lock_timeout_seconds = 5  # Maximum time to wait for a lock

    async def acquire_session_lock(
        self, db: AsyncSession, session_id: UUID, timeout_seconds: Optional[int] = None
    ) -> bool:
        """
        Acquire an advisory lock for a conversation session.

        This ensures only one process can modify a session at a time,
        preventing lost updates from concurrent writers.

        Returns True if lock acquired, False if timeout or lock unavailable.
        """
        timeout = timeout_seconds or self.lock_timeout_seconds

        # PostgreSQL advisory lock using session UUID as lock key
        # Convert UUID to integer for pg_try_advisory_lock
        lock_key = self._uuid_to_lock_key(session_id)

        logger.debug(
            "Attempting to acquire session lock",
            session_id=session_id,
            lock_key=lock_key,
            timeout=timeout,
        )

        try:
            # Try to acquire lock with timeout
            query = text("SELECT pg_try_advisory_lock(:lock_key)")
            result = await db.execute(query, {"lock_key": lock_key})
            acquired = result.scalar()

            if acquired:
                logger.debug(
                    "Session lock acquired", session_id=session_id, lock_key=lock_key
                )
                return True
            else:
                logger.warning(
                    "Failed to acquire session lock immediately",
                    session_id=session_id,
                    lock_key=lock_key,
                )

                # Wait and retry with timeout
                return await self._wait_for_lock(db, lock_key, timeout)

        except Exception as e:
            logger.error(
                "Error acquiring session lock", session_id=session_id, error=str(e)
            )
            return False

    async def release_session_lock(self, db: AsyncSession, session_id: UUID) -> bool:
        """
        Release an advisory lock for a conversation session.

        Returns True if lock released, False if error.
        """
        lock_key = self._uuid_to_lock_key(session_id)

        try:
            query = text("SELECT pg_advisory_unlock(:lock_key)")
            result = await db.execute(query, {"lock_key": lock_key})
            released = result.scalar()

            logger.debug(
                "Session lock release status",
                session_id=session_id,
                lock_key=lock_key,
                released=released,
            )

            return released

        except Exception as e:
            logger.error(
                "Error releasing session lock", session_id=session_id, error=str(e)
            )
            return False

    async def update_session_with_revision_control(
        self,
        db: AsyncSession,
        session_id: UUID,
        expected_revision: Optional[int],
        new_state: Dict[str, Any],
        current_node_id: Optional[str] = None,
        user_initiated: bool = True,
    ) -> tuple[bool, Optional[ConversationSession], Optional[str]]:
        """
        Update session state with revision control to prevent lost updates.

        This implements optimistic concurrency control by checking revision numbers
        and ensures user interactions always win over background tasks.

        Returns:
        - (True, updated_session, None) if update successful
        - (False, current_session, error_message) if conflict detected
        """
        logger.debug(
            "Updating session with revision control",
            session_id=session_id,
            expected_revision=expected_revision,
            user_initiated=user_initiated,
        )

        try:
            # First, get current session state
            query = select(ConversationSession).where(
                ConversationSession.id == session_id
            )
            result = await db.execute(query)
            current_session = result.scalar_one_or_none()

            if not current_session:
                return False, None, "Session not found"

            # Check revision control if expected revision provided
            if expected_revision is not None:
                current_revision = getattr(current_session, "revision", 0) or 0

                if current_revision != expected_revision:
                    # Conflict detected - handle based on priority
                    if user_initiated:
                        # User interactions always win - log override
                        logger.warning(
                            "User interaction overriding background update",
                            session_id=session_id,
                            expected_revision=expected_revision,
                            current_revision=current_revision,
                        )
                    else:
                        # Background task loses to prevent overriding user changes
                        logger.info(
                            "Background task skipped due to concurrent user activity",
                            session_id=session_id,
                            expected_revision=expected_revision,
                            current_revision=current_revision,
                        )
                        return (
                            False,
                            current_session,
                            "Concurrent modification detected",
                        )

            # Update session state
            current_session.state = new_state
            current_session.last_activity_at = datetime.utcnow()

            if current_node_id:
                current_session.current_node_id = current_node_id

            # Increment revision number for next check
            current_revision = getattr(current_session, "revision", 0) or 0
            if hasattr(current_session, "revision"):
                current_session.revision = current_revision + 1

            await db.flush()
            await db.refresh(current_session)

            logger.info(
                "Session updated successfully with revision control",
                session_id=session_id,
                new_revision=getattr(current_session, "revision", None),
                user_initiated=user_initiated,
            )

            return True, current_session, None

        except Exception as e:
            logger.error(
                "Error updating session with revision control",
                session_id=session_id,
                error=str(e),
            )
            return False, None, f"Update error: {str(e)}"

    async def safe_session_update(
        self,
        db: AsyncSession,
        session_id: UUID,
        update_func: callable,
        user_initiated: bool = True,
        timeout_seconds: Optional[int] = None,
    ) -> tuple[bool, Optional[ConversationSession], Optional[str]]:
        """
        Safely update a session with both advisory locks and revision control.

        This is the recommended way to update sessions when you need to prevent
        all forms of concurrent modification.

        Example usage:
        ```python
        def update_logic(session: ConversationSession) -> Dict[str, Any]:
            # Your update logic here
            new_state = session.state.copy()
            new_state["last_user_input"] = "Hello"
            return new_state

        success, session, error = await concurrency_service.safe_session_update(
            db, session_id, update_logic, user_initiated=True
        )
        ```
        """
        # Step 1: Acquire advisory lock
        lock_acquired = await self.acquire_session_lock(db, session_id, timeout_seconds)

        if not lock_acquired:
            return False, None, "Could not acquire session lock"

        try:
            # Step 2: Get current session
            query = select(ConversationSession).where(
                ConversationSession.id == session_id
            )
            result = await db.execute(query)
            current_session = result.scalar_one_or_none()

            if not current_session:
                return False, None, "Session not found"

            # Step 3: Apply update function
            try:
                new_state = update_func(current_session)
                current_revision = getattr(current_session, "revision", 0) or 0

                # Step 4: Update with revision control
                (
                    success,
                    updated_session,
                    error,
                ) = await self.update_session_with_revision_control(
                    db,
                    session_id,
                    current_revision,
                    new_state,
                    user_initiated=user_initiated,
                )

                return success, updated_session, error

            except Exception as e:
                logger.error(
                    "Error in update function", session_id=session_id, error=str(e)
                )
                return False, current_session, f"Update function error: {str(e)}"

        finally:
            # Step 5: Always release the lock
            await self.release_session_lock(db, session_id)

    # PRIVATE METHODS

    def _uuid_to_lock_key(self, session_id: UUID) -> int:
        """Convert UUID to integer for PostgreSQL advisory lock."""
        # Use hash of UUID string to create a consistent integer key
        # This ensures same session always gets same lock key
        uuid_str = str(session_id)
        return hash(uuid_str) % (2**31 - 1)  # Keep within PostgreSQL integer range

    async def _wait_for_lock(
        self, db: AsyncSession, lock_key: int, timeout_seconds: int
    ) -> bool:
        """Wait for lock with timeout using polling."""
        start_time = datetime.utcnow()
        sleep_interval = 0.1  # 100ms polling interval

        while (datetime.utcnow() - start_time).total_seconds() < timeout_seconds:
            try:
                query = text("SELECT pg_try_advisory_lock(:lock_key)")
                result = await db.execute(query, {"lock_key": lock_key})
                acquired = result.scalar()

                if acquired:
                    logger.debug(
                        "Session lock acquired after waiting", lock_key=lock_key
                    )
                    return True

                await asyncio.sleep(sleep_interval)

            except Exception as e:
                logger.error(
                    "Error while waiting for lock", lock_key=lock_key, error=str(e)
                )
                return False

        logger.warning(
            "Lock acquisition timed out", lock_key=lock_key, timeout=timeout_seconds
        )
        return False
