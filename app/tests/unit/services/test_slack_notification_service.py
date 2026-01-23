"""
Unit tests for SlackNotificationService.

This tests the service layer implementation demonstrating proper
separation of concerns and dependency injection patterns.
"""

import json
import os
from unittest.mock import Mock, patch

import pytest

# Set test environment variables before any imports
os.environ.setdefault("POSTGRESQL_PASSWORD", "test")
os.environ.setdefault("SENDGRID_API_KEY", "test")
os.environ.setdefault("SHOPIFY_HMAC_SECRET", "test")
os.environ.setdefault("SECRET_KEY", "test")
os.environ.setdefault("SLACK_BOT_TOKEN", "test-token")

from app.models.event import Event, EventLevel, EventSlackChannel
from app.services.event_outbox_service import EventOutboxService, EventPriority
from app.services.slack_notification import (
    SlackNotificationError,
    SlackNotificationService,
)


class TestSlackNotificationService:
    """Test SlackNotificationService functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_event_outbox_service = Mock(spec=EventOutboxService)
        self.service = SlackNotificationService(self.mock_event_outbox_service)

        # Create a mock event
        self.mock_event = Mock(spec=Event)
        self.mock_event.id = "test-event-id"
        self.mock_event.title = "Test Event"
        self.mock_event.description = "Test event description"
        self.mock_event.level = EventLevel.NORMAL
        self.mock_event.user_id = "user-123"
        self.mock_event.school = None
        self.mock_event.user = None
        self.mock_event.service_account = None
        self.mock_event.info = {"test_key": "test_value"}

    def test_format_event_for_slack(self):
        """Test Slack message formatting."""
        blocks_json, text = self.service._format_event_for_slack(self.mock_event)

        # Verify text format
        assert "Test Event" in text
        assert "Test event description" in text
        assert ":information_source:" in text  # Normal level emoji

        # Verify blocks structure
        blocks = json.loads(blocks_json)
        assert isinstance(blocks, list)
        assert len(blocks) >= 1

        # First block should be the main section
        main_block = blocks[0]
        assert main_block["type"] == "section"
        assert "Test Event" in main_block["text"]["text"]

    def test_format_event_for_slack_with_extra_fields(self):
        """Test Slack message formatting with extra fields."""
        extra = {"deployment": "production", "severity": "high"}
        blocks_json, text = self.service._format_event_for_slack(
            self.mock_event, extra=extra
        )

        blocks = json.loads(blocks_json)

        # Should have info section and extra section
        assert len(blocks) >= 3  # main + info + extra

        # Find the extra section
        extra_section = None
        for block in blocks:
            if block.get("text", {}).get("text") == "*Extra*:":
                extra_section = block
                break

        assert extra_section is not None

    @patch("app.crud.event")
    def test_send_event_alert_via_outbox_sync_success(self, mock_crud_module):
        """Test successful sync outbox sending."""
        # Setup
        mock_session = Mock()
        mock_crud_module.get.return_value = self.mock_event

        # Execute
        self.service.send_event_alert_via_outbox_sync(
            db=mock_session,
            event_id="test-event-id",
            slack_channel=EventSlackChannel.GENERAL,  # Use correct enum value
            priority=EventPriority.HIGH,
            extra={"test": "data"},
        )

        # Verify CRUD was called
        mock_crud_module.get.assert_called_once_with(mock_session, id="test-event-id")

        # Verify outbox service was called
        self.mock_event_outbox_service.publish_event_sync.assert_called_once()
        call_args = self.mock_event_outbox_service.publish_event_sync.call_args

        assert call_args[1]["event_type"] == "slack_notification"
        assert (
            call_args[1]["destination"] == "slack:#api-alerts"
        )  # Use correct channel value
        assert call_args[1]["priority"] == EventPriority.HIGH
        assert call_args[1]["max_retries"] == 5

        # Verify payload structure
        payload = call_args[1]["payload"]
        assert payload["event_id"] == "test-event-id"
        assert payload["slack_channel"] == "#api-alerts"  # Use correct channel value
        assert "slack_blocks" in payload
        assert "slack_text" in payload
        assert payload["extra"] == {"test": "data"}

    @patch("app.crud.event")
    def test_send_event_alert_via_outbox_sync_event_not_found(self, mock_crud_module):
        """Test error handling when event not found."""
        # Setup
        mock_session = Mock()
        mock_crud_module.get.return_value = None

        # Execute and verify exception
        with pytest.raises(
            SlackNotificationError, match="Event test-event-id not found"
        ):
            self.service.send_event_alert_via_outbox_sync(
                db=mock_session,
                event_id="test-event-id",
                slack_channel=EventSlackChannel.GENERAL,
            )

        # Verify outbox service was not called
        self.mock_event_outbox_service.publish_event_sync.assert_not_called()

    @patch("app.crud.event")
    @patch("app.services.slack_notification.WebClient")
    @patch("app.services.slack_notification.config")
    def test_send_event_alert_direct_sync_success(
        self, mock_config, mock_web_client, mock_crud_module
    ):
        """Test successful direct sync Slack sending."""
        # Setup
        mock_session = Mock()
        mock_crud_module.get.return_value = self.mock_event
        mock_config.SLACK_BOT_TOKEN = "test-token"

        mock_client_instance = Mock()
        mock_web_client.return_value = mock_client_instance
        mock_client_instance.chat_postMessage.return_value = {"ts": "123456"}

        # Execute
        result = self.service.send_event_alert_direct_sync(
            db=mock_session,
            event_id="test-event-id",
            slack_channel=EventSlackChannel.GENERAL,
            extra={"test": "data"},
        )

        # Verify result
        assert result is True

        # Verify Slack client was called correctly
        mock_web_client.assert_called_once_with(token="test-token")
        mock_client_instance.chat_postMessage.assert_called_once()

        call_args = mock_client_instance.chat_postMessage.call_args
        assert call_args[1]["channel"] == "#api-alerts"
        assert "blocks" in call_args[1]
        assert "text" in call_args[1]

    @patch("app.crud.event")
    @patch("app.services.slack_notification.config")
    def test_send_event_alert_direct_sync_no_token(self, mock_config, mock_crud_module):
        """Test direct sync sending without Slack token."""
        # Setup
        mock_session = Mock()
        mock_crud_module.get.return_value = self.mock_event
        mock_config.SLACK_BOT_TOKEN = None

        # Execute
        result = self.service.send_event_alert_direct_sync(
            db=mock_session,
            event_id="test-event-id",
            slack_channel=EventSlackChannel.GENERAL,
        )

        # Verify result - should return False but not raise exception
        assert result is False

    async def test_process_outbox_slack_notification_success(self):
        """Test processing outbox notification successfully."""
        # Setup
        payload = {
            "event_id": "test-event-id",
            "slack_channel": "#api-alerts",
            "slack_blocks": json.dumps(
                [{"type": "section", "text": {"type": "mrkdwn", "text": "Test"}}]
            ),
            "slack_text": "Test message",
            "extra": {},
        }

        with patch.object(
            self.service, "_send_slack_message_sync", return_value=True
        ) as mock_send:
            result = await self.service.process_outbox_slack_notification(payload)

        # Verify result
        assert result is True

        # Verify message was sent
        mock_send.assert_called_once_with(
            channel="#api-alerts",
            blocks=payload["slack_blocks"],
            text=payload["slack_text"],
        )

    async def test_process_outbox_slack_notification_invalid_payload(self):
        """Test processing invalid outbox notification payload."""
        # Setup - missing required fields
        payload = {
            "event_id": "test-event-id",
            "slack_channel": "#api-alerts",
            # Missing slack_blocks and slack_text
        }

        # Execute
        result = await self.service.process_outbox_slack_notification(payload)

        # Verify result - should return False for invalid payload (don't retry)
        assert result is False


class TestSlackNotificationConvenienceFunctions:
    """Test convenience functions for backward compatibility."""

    @patch("app.services.slack_notification.create_slack_notification_service")
    def test_send_slack_alert_reliable_sync(self, mock_create_service):
        """Test sync reliable alert sending convenience function."""
        mock_service = Mock()
        mock_create_service.return_value = mock_service
        mock_session = Mock()

        from app.services.slack_notification import send_slack_alert_reliable_sync

        # Execute
        send_slack_alert_reliable_sync(
            db=mock_session,
            event_id="test-event-id",
            slack_channel=EventSlackChannel.GENERAL,  # Use correct enum value
            extra={"test": "data"},
            priority=EventPriority.HIGH,
        )

        # Verify service was created and called correctly
        mock_create_service.assert_called_once()
        mock_service.send_event_alert_via_outbox_sync.assert_called_once_with(
            db=mock_session,
            event_id="test-event-id",
            slack_channel=EventSlackChannel.GENERAL,
            priority=EventPriority.HIGH,
            extra={"test": "data"},
        )

    @patch("app.services.slack_notification.create_slack_notification_service")
    def test_send_slack_alert_immediate_sync(self, mock_create_service):
        """Test sync immediate alert sending convenience function."""
        mock_service = Mock()
        mock_service.send_event_alert_direct_sync.return_value = True
        mock_create_service.return_value = mock_service
        mock_session = Mock()

        from app.services.slack_notification import send_slack_alert_immediate_sync

        # Execute
        result = send_slack_alert_immediate_sync(
            db=mock_session,
            event_id="test-event-id",
            slack_channel=EventSlackChannel.GENERAL,  # Use correct enum value
            extra={"test": "data"},
        )

        # Verify result and service calls
        assert result is True
        mock_create_service.assert_called_once()
        mock_service.send_event_alert_direct_sync.assert_called_once_with(
            db=mock_session,
            event_id="test-event-id",
            slack_channel=EventSlackChannel.GENERAL,
            extra={"test": "data"},
        )
