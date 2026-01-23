"""
Integration tests for the outbox-based webhook delivery system.

These tests verify that:
1. EventOutboxService correctly delivers webhooks via HTTP
2. FlowWebhookService creates outbox entries from flow events
3. WebhookSubscription filtering works correctly
4. Retry logic and error handling work as expected
5. HMAC signature generation is correct
"""

import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cms import FlowDefinition
from app.models.event_outbox import EventStatus
from app.models.webhook_subscription import (
    WebhookSubscription,
    WebhookSubscriptionStatus,
)
from app.services.event_listener import FlowEvent
from app.services.event_outbox_service import (
    EventOutboxService,
    close_http_client,
    get_http_client,
)
from app.services.flow_webhook_service import (
    FlowWebhookService,
    reset_flow_webhook_service,
)

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
async def cleanup_webhook_data(async_session: AsyncSession):
    """Clean up webhook-related data before and after each test."""
    tables = [
        "event_outbox",
        "webhook_subscriptions",
        "conversation_sessions",
        "flow_definitions",
    ]

    await async_session.rollback()

    for table in tables:
        try:
            await async_session.execute(
                text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
            )
        except Exception:
            pass
    await async_session.commit()

    yield

    await async_session.rollback()

    for table in tables:
        try:
            await async_session.execute(
                text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
            )
        except Exception:
            pass
    await async_session.commit()


@pytest.fixture
async def test_flow(async_session: AsyncSession) -> FlowDefinition:
    """Create a test flow definition."""
    flow = FlowDefinition(
        id=uuid.uuid4(),
        name="Webhook Test Flow",
        description="Flow for testing webhook delivery",
        version="1.0.0",
        flow_data={"nodes": [], "connections": []},
        entry_node_id="start",
        is_published=True,
        is_active=True,
    )

    async_session.add(flow)
    await async_session.commit()
    await async_session.refresh(flow)

    return flow


@pytest.fixture
async def test_webhook_subscription(
    async_session: AsyncSession, test_flow: FlowDefinition
) -> WebhookSubscription:
    """Create a test webhook subscription."""
    subscription = WebhookSubscription(
        id=uuid.uuid4(),
        name="Test Webhook",
        url="https://example.com/webhook",
        secret="test-secret-key",
        method="POST",
        headers={"X-Custom-Header": "test-value"},
        timeout_seconds=30,
        max_retries=3,
        event_types=[],  # Subscribe to all events
        flow_id=test_flow.id,
        status=WebhookSubscriptionStatus.ACTIVE,
    )

    async_session.add(subscription)
    await async_session.commit()
    await async_session.refresh(subscription)

    return subscription


@pytest.fixture
def outbox_service() -> EventOutboxService:
    """Create an EventOutboxService instance."""
    return EventOutboxService()


@pytest.fixture
def flow_webhook_service() -> FlowWebhookService:
    """Create a FlowWebhookService instance."""
    reset_flow_webhook_service()
    return FlowWebhookService()


class TestEventOutboxWebhookDelivery:
    """Test EventOutboxService webhook delivery functionality."""

    async def test_deliver_webhook_test_mode_success(
        self, outbox_service: EventOutboxService, async_session: AsyncSession
    ):
        """Test that test mode webhooks simulate success correctly."""
        event = await outbox_service.publish_event(
            async_session,
            event_type="test_event",
            destination="webhook_test",
            payload={"simulate_success": True, "data": "test"},
        )
        await async_session.commit()

        result = await outbox_service._deliver_webhook(event)
        assert result is True

    async def test_deliver_webhook_test_mode_failure(
        self, outbox_service: EventOutboxService, async_session: AsyncSession
    ):
        """Test that test mode webhooks simulate failure correctly."""
        event = await outbox_service.publish_event(
            async_session,
            event_type="test_event",
            destination="webhook_test",
            payload={"simulate_success": False},
        )
        await async_session.commit()

        result = await outbox_service._deliver_webhook(event)
        assert result is False

    async def test_deliver_webhook_test_mode_http_error(
        self, outbox_service: EventOutboxService, async_session: AsyncSession
    ):
        """Test that test mode webhooks simulate HTTP errors correctly."""
        event = await outbox_service.publish_event(
            async_session,
            event_type="test_event",
            destination="webhook_test",
            payload={"simulate_status_code": 500},
        )
        await async_session.commit()

        result = await outbox_service._deliver_webhook(event)
        assert result is False

    async def test_deliver_webhook_test_mode_timeout(
        self, outbox_service: EventOutboxService, async_session: AsyncSession
    ):
        """Test that test mode webhooks simulate timeout correctly."""
        event = await outbox_service.publish_event(
            async_session,
            event_type="test_event",
            destination="webhook_test",
            payload={"simulate_timeout": True},
        )
        await async_session.commit()

        with pytest.raises(httpx.TimeoutException):
            await outbox_service._deliver_webhook(event)

    async def test_deliver_webhook_invalid_destination_format(
        self, outbox_service: EventOutboxService, async_session: AsyncSession
    ):
        """Test that invalid destination format returns False."""
        event = await outbox_service.publish_event(
            async_session,
            event_type="test_event",
            destination="invalid_destination",
            payload={"data": "test"},
        )
        await async_session.commit()

        result = await outbox_service._deliver_webhook(event)
        assert result is False

    @pytest.mark.parametrize(
        "status_code,expected_success",
        [
            (200, True),
            (201, True),
            (202, True),
            (204, True),
            (301, True),
            (400, False),
            (401, False),
            (403, False),
            (404, False),
            (500, False),
            (502, False),
            (503, False),
        ],
    )
    async def test_deliver_webhook_status_codes(
        self,
        outbox_service: EventOutboxService,
        async_session: AsyncSession,
        status_code: int,
        expected_success: bool,
    ):
        """Test webhook delivery handles various HTTP status codes correctly."""
        event = await outbox_service.publish_event(
            async_session,
            event_type="test_event",
            destination="webhook:https://httpbin.org/status/" + str(status_code),
            payload={"data": "test"},
        )
        await async_session.commit()

        # Mock the HTTP client to avoid actual network calls
        mock_response = MagicMock()
        mock_response.status_code = status_code
        mock_response.text = "Test response"

        with patch.object(
            httpx.AsyncClient,
            "post",
            return_value=mock_response,
        ):
            # Get a client to patch
            client = await get_http_client()
            with patch.object(client, "post", return_value=mock_response):
                result = await outbox_service._deliver_webhook(event)
                assert result is expected_success


class TestWebhookHMACSignature:
    """Test HMAC signature generation for webhooks."""

    async def test_hmac_signature_generated_when_secret_provided(
        self, outbox_service: EventOutboxService, async_session: AsyncSession
    ):
        """Test that HMAC signature is generated when secret is provided."""
        secret = "my-webhook-secret"
        payload = {"event_type": "test", "data": "test_data"}

        event = await outbox_service.publish_event(
            async_session,
            event_type="test_event",
            destination="webhook:https://example.com/hook",
            payload=payload,
            headers={"secret": secret},
        )
        await async_session.commit()

        # Calculate expected signature
        payload_json = json.dumps(payload, default=str)
        expected_signature = hmac.new(
            secret.encode("utf-8"),
            payload_json.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        # Capture the actual request headers
        captured_headers = {}

        async def capture_request(*args, **kwargs):
            nonlocal captured_headers
            captured_headers = dict(kwargs.get("headers", {}))
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "OK"
            return mock_response

        client = await get_http_client()
        with patch.object(client, "post", side_effect=capture_request):
            await outbox_service._deliver_webhook(event)

        assert "X-Webhook-Signature" in captured_headers
        assert captured_headers["X-Webhook-Signature"] == f"sha256={expected_signature}"

    async def test_no_signature_when_no_secret(
        self, outbox_service: EventOutboxService, async_session: AsyncSession
    ):
        """Test that no signature is added when secret is not provided."""
        event = await outbox_service.publish_event(
            async_session,
            event_type="test_event",
            destination="webhook:https://example.com/hook",
            payload={"data": "test"},
        )
        await async_session.commit()

        captured_headers = {}

        async def capture_request(*args, **kwargs):
            nonlocal captured_headers
            captured_headers = dict(kwargs.get("headers", {}))
            mock_response = MagicMock()
            mock_response.status_code = 200
            return mock_response

        client = await get_http_client()
        with patch.object(client, "post", side_effect=capture_request):
            await outbox_service._deliver_webhook(event)

        assert "X-Webhook-Signature" not in captured_headers


class TestWebhookSubscriptionFiltering:
    """Test WebhookSubscription event filtering."""

    async def test_matches_event_all_events(
        self, async_session: AsyncSession, test_flow: FlowDefinition
    ):
        """Test subscription with empty event_types matches all events."""
        subscription = WebhookSubscription(
            id=uuid.uuid4(),
            name="All Events Webhook",
            url="https://example.com/all",
            event_types=[],  # Empty = all events
            status=WebhookSubscriptionStatus.ACTIVE,
        )
        async_session.add(subscription)
        await async_session.commit()

        assert subscription.matches_event("session_started")
        assert subscription.matches_event("node_changed")
        assert subscription.matches_event("session_completed")

    async def test_matches_event_specific_events(
        self, async_session: AsyncSession, test_flow: FlowDefinition
    ):
        """Test subscription with specific event_types only matches those events."""
        subscription = WebhookSubscription(
            id=uuid.uuid4(),
            name="Specific Events Webhook",
            url="https://example.com/specific",
            event_types=["session_started", "session_completed"],
            status=WebhookSubscriptionStatus.ACTIVE,
        )
        async_session.add(subscription)
        await async_session.commit()

        assert subscription.matches_event("session_started")
        assert subscription.matches_event("session_completed")
        assert not subscription.matches_event("node_changed")
        assert not subscription.matches_event("session_updated")

    async def test_matches_event_flow_filter(
        self, async_session: AsyncSession, test_flow: FlowDefinition
    ):
        """Test subscription with flow_id only matches events from that flow."""
        subscription = WebhookSubscription(
            id=uuid.uuid4(),
            name="Flow Specific Webhook",
            url="https://example.com/flow",
            event_types=[],
            flow_id=test_flow.id,
            status=WebhookSubscriptionStatus.ACTIVE,
        )
        async_session.add(subscription)
        await async_session.commit()

        # Should match events from the specific flow
        assert subscription.matches_event("session_started", test_flow.id)

        # Should not match events from other flows
        other_flow_id = uuid.uuid4()
        assert not subscription.matches_event("session_started", other_flow_id)

    async def test_matches_event_inactive_subscription(
        self, async_session: AsyncSession
    ):
        """Test inactive subscriptions don't match any events."""
        subscription = WebhookSubscription(
            id=uuid.uuid4(),
            name="Inactive Webhook",
            url="https://example.com/inactive",
            event_types=[],
            status=WebhookSubscriptionStatus.PAUSED,
        )
        async_session.add(subscription)
        await async_session.commit()

        assert not subscription.matches_event("session_started")

    async def test_subscription_health_tracking(self, async_session: AsyncSession):
        """Test subscription health tracking properties."""
        subscription = WebhookSubscription(
            id=uuid.uuid4(),
            name="Health Test Webhook",
            url="https://example.com/health",
            event_types=[],
            status=WebhookSubscriptionStatus.ACTIVE,
            consecutive_failures=0,
        )
        async_session.add(subscription)
        await async_session.commit()

        # Initially healthy
        assert subscription.is_healthy

        # Record failures
        for i in range(4):
            subscription.record_failure(f"Error {i}")
            assert subscription.is_healthy

        # 5th failure should make it unhealthy
        subscription.record_failure("Error 5")
        assert not subscription.is_healthy

        # Success should reset health
        subscription.record_success()
        assert subscription.is_healthy
        assert subscription.consecutive_failures == 0


class TestFlowWebhookService:
    """Test FlowWebhookService functionality."""

    async def test_publish_flow_event_creates_outbox_entries(
        self,
        async_session: AsyncSession,
        test_flow: FlowDefinition,
        test_webhook_subscription: WebhookSubscription,
        flow_webhook_service: FlowWebhookService,
    ):
        """Test that publishing a flow event creates outbox entries for matching subscriptions."""
        event = FlowEvent(
            event_type="session_started",
            session_id=uuid.uuid4(),
            flow_id=test_flow.id,
            timestamp=datetime.utcnow().timestamp(),
            user_id=None,
            current_node="start",
            status="ACTIVE",
            revision=1,
        )

        entries = await flow_webhook_service.publish_flow_event(async_session, event)
        await async_session.commit()

        assert len(entries) == 1
        entry = entries[0]
        assert entry.event_type == "flow_webhook:session_started"
        assert entry.destination == f"webhook:{test_webhook_subscription.url}"
        assert entry.status == EventStatus.PENDING
        assert entry.flow_id == test_flow.id
        assert entry.session_id == event.session_id

    async def test_publish_flow_event_no_matching_subscriptions(
        self,
        async_session: AsyncSession,
        test_flow: FlowDefinition,
        flow_webhook_service: FlowWebhookService,
    ):
        """Test that no outbox entries are created when no subscriptions match."""
        event = FlowEvent(
            event_type="session_started",
            session_id=uuid.uuid4(),
            flow_id=test_flow.id,
            timestamp=datetime.utcnow().timestamp(),
        )

        entries = await flow_webhook_service.publish_flow_event(async_session, event)
        await async_session.commit()

        assert len(entries) == 0

    async def test_publish_flow_event_multiple_subscriptions(
        self,
        async_session: AsyncSession,
        test_flow: FlowDefinition,
        flow_webhook_service: FlowWebhookService,
    ):
        """Test that multiple matching subscriptions each get an outbox entry."""
        # Create multiple subscriptions
        for i in range(3):
            subscription = WebhookSubscription(
                id=uuid.uuid4(),
                name=f"Webhook {i}",
                url=f"https://example{i}.com/webhook",
                event_types=[],
                flow_id=test_flow.id,
                status=WebhookSubscriptionStatus.ACTIVE,
            )
            async_session.add(subscription)
        await async_session.commit()

        event = FlowEvent(
            event_type="session_started",
            session_id=uuid.uuid4(),
            flow_id=test_flow.id,
            timestamp=datetime.utcnow().timestamp(),
        )

        entries = await flow_webhook_service.publish_flow_event(async_session, event)
        await async_session.commit()

        assert len(entries) == 3

    async def test_publish_flow_event_includes_secret_in_headers(
        self,
        async_session: AsyncSession,
        test_flow: FlowDefinition,
        test_webhook_subscription: WebhookSubscription,
        flow_webhook_service: FlowWebhookService,
    ):
        """Test that webhook secret is included in outbox entry headers."""
        event = FlowEvent(
            event_type="session_started",
            session_id=uuid.uuid4(),
            flow_id=test_flow.id,
            timestamp=datetime.utcnow().timestamp(),
        )

        entries = await flow_webhook_service.publish_flow_event(async_session, event)
        await async_session.commit()

        assert len(entries) == 1
        entry = entries[0]
        assert entry.headers is not None
        assert "secret" in entry.headers
        assert entry.headers["secret"] == test_webhook_subscription.secret


class TestOutboxProcessorIntegration:
    """Test the full outbox processor flow with webhooks."""

    async def test_process_pending_webhook_events_success(
        self, outbox_service: EventOutboxService, async_session: AsyncSession
    ):
        """Test that pending webhook events are processed successfully."""
        # Create a pending webhook event
        event = await outbox_service.publish_event(
            async_session,
            event_type="test_event",
            destination="webhook_test",
            payload={"simulate_success": True},
        )
        await async_session.commit()

        # Process pending events
        stats = await outbox_service.process_pending_events(async_session)

        assert stats["processed"] == 1
        assert stats["succeeded"] == 1
        assert stats["failed"] == 0

        # Verify event status updated
        await async_session.refresh(event)
        assert event.status == EventStatus.PUBLISHED
        assert event.processed_at is not None

    async def test_process_pending_webhook_events_failure_with_retry(
        self, outbox_service: EventOutboxService, async_session: AsyncSession
    ):
        """Test that failed webhook events are scheduled for retry."""
        event = await outbox_service.publish_event(
            async_session,
            event_type="test_event",
            destination="webhook_test",
            payload={"simulate_success": False},
            max_retries=3,
        )
        await async_session.commit()

        # Process pending events
        stats = await outbox_service.process_pending_events(async_session)

        assert stats["processed"] == 1
        assert stats["failed"] == 1

        # Verify event is scheduled for retry
        await async_session.refresh(event)
        assert event.status == EventStatus.FAILED
        assert event.retry_count == 1
        assert event.next_retry_at is not None
        assert event.last_error is not None

    async def test_process_pending_webhook_events_dead_letter(
        self, outbox_service: EventOutboxService, async_session: AsyncSession
    ):
        """Test that events exceeding max retries go to dead letter queue."""
        event = await outbox_service.publish_event(
            async_session,
            event_type="test_event",
            destination="webhook_test",
            payload={"simulate_success": False},
            max_retries=0,  # No retries allowed
        )
        await async_session.commit()

        # Process twice to exceed max retries
        await outbox_service.process_pending_events(async_session)

        # Verify event is in dead letter queue
        await async_session.refresh(event)
        assert event.status == EventStatus.DEAD_LETTER

    async def test_retry_event_resets_status(
        self, outbox_service: EventOutboxService, async_session: AsyncSession
    ):
        """Test that retry_event resets a failed event for reprocessing."""
        event = await outbox_service.publish_event(
            async_session,
            event_type="test_event",
            destination="webhook_test",
            payload={"simulate_success": False},
        )
        await async_session.commit()

        # Process to fail the event
        await outbox_service.process_pending_events(async_session)

        # Retry the event
        success = await outbox_service.retry_event(async_session, event.id)
        assert success

        await async_session.refresh(event)
        assert event.status == EventStatus.PENDING
        assert event.retry_count == 0
        assert event.next_retry_at is None


class TestWebhookPayloadStructure:
    """Test the structure of webhook payloads."""

    async def test_flow_event_payload_contains_required_fields(
        self,
        async_session: AsyncSession,
        test_flow: FlowDefinition,
        test_webhook_subscription: WebhookSubscription,
        flow_webhook_service: FlowWebhookService,
    ):
        """Test that flow event payloads contain all required fields."""
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        event = FlowEvent(
            event_type="session_started",
            session_id=session_id,
            flow_id=test_flow.id,
            timestamp=1234567890.123,
            user_id=user_id,
            current_node="start_node",
            previous_node=None,
            status="ACTIVE",
            previous_status=None,
            revision=1,
            previous_revision=None,
        )

        entries = await flow_webhook_service.publish_flow_event(async_session, event)
        await async_session.commit()

        assert len(entries) == 1
        payload = entries[0].payload

        assert payload["event_type"] == "session_started"
        assert payload["session_id"] == str(session_id)
        assert payload["flow_id"] == str(test_flow.id)
        assert payload["timestamp"] == 1234567890.123
        assert payload["user_id"] == str(user_id)

        data = payload["data"]
        assert data["current_node"] == "start_node"
        assert data["previous_node"] is None
        assert data["status"] == "ACTIVE"
        assert data["revision"] == 1


class TestConcurrentWebhookDelivery:
    """Test concurrent webhook delivery scenarios."""

    async def test_multiple_events_processed_concurrently(
        self, outbox_service: EventOutboxService, async_session: AsyncSession
    ):
        """Test that multiple events can be processed without interference."""
        # Create multiple pending events
        for i in range(5):
            await outbox_service.publish_event(
                async_session,
                event_type=f"test_event_{i}",
                destination="webhook_test",
                payload={"simulate_success": True, "index": i},
            )
        await async_session.commit()

        # Process all pending events
        stats = await outbox_service.process_pending_events(async_session)

        assert stats["processed"] == 5
        assert stats["succeeded"] == 5
        assert stats["failed"] == 0


@pytest.fixture(autouse=True)
async def cleanup_http_client():
    """Clean up HTTP client after tests."""
    yield
    await close_http_client()
