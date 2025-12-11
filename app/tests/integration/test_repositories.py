"""
Integration tests for the new repository and service architecture.
"""

from app.models.cms import ContentType
from app.repositories.cms_repository import CMSRepositoryImpl
from app.repositories.conversation_repository import ConversationRepositoryImpl
from app.services.conversation_service import ConversationService


class TestRepositoryArchitecture:
    """Test the new domain repository architecture."""

    async def test_conversation_repository_instantiation(self, async_session):
        """Test that conversation repository can be instantiated."""
        repo = ConversationRepositoryImpl()
        assert repo is not None

    async def test_cms_repository_instantiation(self, async_session):
        """Test that CMS repository can be instantiated."""
        repo = CMSRepositoryImpl()
        assert repo is not None

    async def test_conversation_service_with_dependencies(self, async_session):
        """Test conversation service with injected dependencies."""
        conv_repo = ConversationRepositoryImpl()
        cms_repo = CMSRepositoryImpl()
        service = ConversationService(conv_repo, cms_repo)

        assert service.conversation_repo is conv_repo
        assert service.cms_repo is cms_repo

    async def test_conversation_service_default_dependencies(self, async_session):
        """Test conversation service with default dependencies."""
        service = ConversationService()

        assert isinstance(service.conversation_repo, ConversationRepositoryImpl)
        assert isinstance(service.cms_repo, CMSRepositoryImpl)

    async def test_get_active_session_by_token_not_found(self, async_session):
        """Test getting non-existent session returns None."""
        repo = ConversationRepositoryImpl()

        session = await repo.get_active_session_by_token(
            async_session, "non-existent-token"
        )
        assert session is None

    async def test_find_published_flows_empty(self, async_session):
        """Test finding published flows when none exist."""
        repo = CMSRepositoryImpl()

        flows = await repo.find_published_flows(async_session)
        assert isinstance(flows, list)
        # May be empty if no flows in test DB

    async def test_find_content_by_type_empty(self, async_session):
        """Test finding content by type when none exists."""
        repo = CMSRepositoryImpl()

        content = await repo.find_content_by_type_and_tags(
            async_session, ContentType.JOKE, ["test"]
        )
        assert isinstance(content, list)

    async def test_conversation_service_get_state_not_found(self, async_session):
        """Test getting conversation state for non-existent session."""
        service = ConversationService()

        state = await service.get_conversation_state(async_session, "non-existent")
        assert state is None

    async def test_conversation_service_get_history_empty(self, async_session):
        """Test getting conversation history for non-existent session."""
        service = ConversationService()

        history = await service.get_conversation_history(async_session, "non-existent")
        assert history == []
