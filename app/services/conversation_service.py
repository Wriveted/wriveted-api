"""
Conversation Service - Domain service for managing conversation flows.

This service demonstrates CQRS-Lite patterns by separating read and write
operations and using domain repositories instead of generic CRUD.
"""

from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.models.cms import ConversationSession, InteractionType, SessionStatus
from app.repositories.cms_repository import CMSRepository, CMSRepositoryImpl
from app.repositories.conversation_repository import (
    ConversationRepository,
    ConversationRepositoryImpl,
)

logger = get_logger()


class ConversationService:
    """
    Domain service for conversation management.

    This service demonstrates proper service layer architecture:
    - Uses domain repositories instead of generic CRUD
    - Separates read and write operations (CQRS-Lite)
    - Contains business logic for conversation flows
    - Maintains transaction boundaries appropriately
    """

    def __init__(
        self,
        conversation_repo: Optional[ConversationRepository] = None,
        cms_repo: Optional[CMSRepository] = None,
    ):
        # Dependency injection for testability
        self.conversation_repo = conversation_repo or ConversationRepositoryImpl()
        self.cms_repo = cms_repo or CMSRepositoryImpl()

    # WRITE OPERATIONS - Use transactions for consistency

    async def start_conversation(
        self,
        db: AsyncSession,
        flow_id: UUID,
        user_id: Optional[UUID] = None,
        initial_context: Optional[Dict] = None,
    ) -> Tuple[ConversationSession, Dict]:
        """
        Start a new conversation session.

        This is a WRITE operation that requires transaction consistency.
        Returns both the session and the first interaction response.
        """
        logger.info("Starting conversation", flow_id=flow_id, user_id=user_id)

        # Validate flow exists and is published
        flow = await self.cms_repo.get_flow_with_nodes(db, flow_id)
        if not flow or not flow.is_published:
            raise ValueError(f"Flow {flow_id} not found or not published")

        # Initialize session state
        initial_state = {
            "flow_id": str(flow_id),
            "user_context": initial_context or {},
            "variables": {},
            "history": [],
            "started_at": "now",
        }

        # Create session - this is a write operation requiring transaction
        session = await self.conversation_repo.start_new_conversation(
            db, flow_id, user_id, initial_state
        )

        # Add initial interaction to history
        await self.conversation_repo.add_interaction_to_history(
            db,
            session,
            flow.entry_node_id,
            InteractionType.SYSTEM,
            {"action": "session_started", "flow_id": str(flow_id)},
        )

        # Generate first response (business logic)
        first_response = await self._generate_node_response(
            db, session, flow.entry_node_id
        )

        logger.info(
            "Started conversation successfully",
            session_id=session.id,
            session_token=session.session_token,
        )

        return session, first_response

    async def process_user_interaction(
        self,
        db: AsyncSession,
        session_token: str,
        user_input: str,
        input_type: str = "text",
    ) -> Dict:
        """
        Process user interaction and generate response.

        This is a WRITE operation that updates session state and history.
        """
        logger.info("Processing user interaction", session_token=session_token)

        # Get active session - read operation
        session = await self.conversation_repo.get_active_session_by_token(
            db, session_token
        )
        if not session:
            raise ValueError("Session not found or inactive")

        # Record user interaction - write operation
        await self.conversation_repo.add_interaction_to_history(
            db,
            session,
            session.current_node_id or "unknown",
            InteractionType.INPUT,
            {"input": user_input, "input_type": input_type},
        )

        # Process flow logic and determine next node (business logic)
        next_node_id = await self._determine_next_node(db, session, user_input)

        # Update session state - write operation
        updated_state = session.state.copy()
        updated_state["last_input"] = user_input
        updated_state["last_input_type"] = input_type

        session = await self.conversation_repo.update_session_state(
            db, session, updated_state, next_node_id
        )

        # Generate response for next node
        response = await self._generate_node_response(db, session, next_node_id)

        logger.info(
            "Processed interaction successfully",
            session_id=session.id,
            next_node=next_node_id,
        )

        return response

    async def end_conversation(
        self,
        db: AsyncSession,
        session_token: str,
        status: SessionStatus = SessionStatus.COMPLETED,
    ) -> ConversationSession:
        """
        End a conversation session.

        This is a WRITE operation that finalizes the session.
        """
        logger.info("Ending conversation", session_token=session_token)

        session = await self.conversation_repo.get_active_session_by_token(
            db, session_token
        )
        if not session:
            raise ValueError("Session not found or already ended")

        # Record session end in history
        await self.conversation_repo.add_interaction_to_history(
            db,
            session,
            session.current_node_id or "unknown",
            InteractionType.SYSTEM,
            {"action": "session_ended", "status": status.value},
        )

        # End session - write operation
        session = await self.conversation_repo.end_conversation(db, session, status)

        logger.info(
            "Ended conversation successfully",
            session_id=session.id,
            status=status.value,
        )

        return session

    # READ OPERATIONS - Direct repository access, no transactions needed

    async def get_conversation_state(
        self, db: AsyncSession, session_token: str
    ) -> Optional[Dict]:
        """
        Get current conversation state.

        This is a READ operation - no transaction needed.
        """
        session = await self.conversation_repo.get_active_session_by_token(
            db, session_token
        )
        if not session:
            return None

        return {
            "session_id": str(session.id),
            "session_token": session.session_token,
            "flow_id": str(session.flow_id),
            "current_node": session.current_node_id,
            "status": session.status.value,
            "state": session.state,
            "started_at": session.started_at.isoformat()
            if session.started_at
            else None,
            "last_activity": session.last_activity_at.isoformat()
            if session.last_activity_at
            else None,
        }

    async def get_conversation_history(
        self,
        db: AsyncSession,
        session_token: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict]:
        """
        Get conversation history.

        This is a READ operation - no transaction needed.
        """
        session = await self.conversation_repo.get_active_session_by_token(
            db, session_token
        )
        if not session:
            return []

        history = await self.conversation_repo.get_conversation_history(
            db, session, limit, offset
        )

        return [
            {
                "id": str(interaction.id),
                "node_id": interaction.node_id,
                "interaction_type": interaction.interaction_type.value,
                "content": interaction.content,
                "created_at": interaction.created_at.isoformat(),
            }
            for interaction in history
        ]

    # PRIVATE BUSINESS LOGIC METHODS

    async def _determine_next_node(
        self, db: AsyncSession, session: ConversationSession, user_input: str
    ) -> str:
        """Determine the next node based on current state and user input."""
        # Simplified flow logic - in real implementation would evaluate conditions
        current_node = session.current_node_id

        # Business logic for flow navigation
        if current_node == "welcome":
            return "ask_name"
        elif current_node == "ask_name":
            return "greet_user"
        else:
            return "end_flow"

    async def _generate_node_response(
        self, db: AsyncSession, session: ConversationSession, node_id: str
    ) -> Dict:
        """Generate response for a specific node."""
        # Simplified response generation - real implementation would use node processor
        return {
            "node_id": node_id,
            "messages": [
                {
                    "type": "text",
                    "content": f"Response from node: {node_id}",
                    "delay": 1.0,
                }
            ],
            "expects_input": node_id not in ["end_flow"],
            "input_type": "text" if node_id not in ["end_flow"] else None,
        }
