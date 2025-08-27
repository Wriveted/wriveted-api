"""
Webhook notification service for flow state changes.

This service sends HTTP webhook notifications to external services when
flow events occur, enabling real-time integration with external systems.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, cast

import httpx
from pydantic import BaseModel, HttpUrl

from app.services.event_listener import FlowEvent

logger = logging.getLogger(__name__)


class WebhookConfig(BaseModel):
    """Configuration for a webhook endpoint."""

    url: HttpUrl
    secret: Optional[str] = None  # Optional webhook secret for HMAC verification
    events: List[str] = ["*"]  # Event types to send (["*"] for all)
    headers: Dict[str, str] = {}  # Additional headers to send
    timeout: int = 10  # Request timeout in seconds
    retry_attempts: int = 3  # Number of retry attempts
    retry_delay: int = 1  # Base delay between retries in seconds


class WebhookPayload(BaseModel):
    """Payload structure for webhook notifications."""

    event_type: str
    timestamp: float
    session_id: str
    flow_id: str
    user_id: Optional[str] = None
    data: Dict[str, Any]  # Event-specific data


class WebhookNotifier:
    """
    Service for sending webhook notifications on flow events.

    Manages webhook configurations and handles reliable delivery with retries.
    """

    def __init__(self):
        self.webhooks: List[WebhookConfig] = []
        self.client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> None:
        """Initialize the HTTP client for webhook delivery."""
        if not self.client:
            self.client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0), follow_redirects=True
            )

    async def shutdown(self) -> None:
        """Shutdown the HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None

    def add_webhook(self, webhook: WebhookConfig) -> None:
        """Add a webhook configuration."""
        self.webhooks.append(webhook)
        logger.info(f"Added webhook: {webhook.url} for events: {webhook.events}")

    def remove_webhook(self, url: str) -> None:
        """Remove a webhook configuration by URL."""
        self.webhooks = [w for w in self.webhooks if str(w.url) != url]
        logger.info(f"Removed webhook: {url}")

    async def notify_event(self, event: FlowEvent) -> None:
        """
        Send webhook notifications for a flow event.

        Args:
            event: The flow event to notify about
        """
        if not self.client:
            await self.initialize()

        # Find webhooks that should receive this event
        matching_webhooks = [
            webhook
            for webhook in self.webhooks
            if "*" in webhook.events or event.event_type in webhook.events
        ]

        if not matching_webhooks:
            logger.debug(f"No webhooks configured for event type: {event.event_type}")
            return

        # Create webhook payload
        payload = WebhookPayload(
            event_type=event.event_type,
            timestamp=event.timestamp,
            session_id=str(event.session_id),
            flow_id=str(event.flow_id),
            user_id=str(event.user_id) if event.user_id else None,
            data={
                "current_node": event.current_node,
                "previous_node": event.previous_node,
                "status": event.status,
                "previous_status": event.previous_status,
                "revision": event.revision,
                "previous_revision": event.previous_revision,
            },
        )

        # Send notifications concurrently
        tasks = [self._send_webhook(webhook, payload) for webhook in matching_webhooks]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Log results
        for webhook, result in zip(matching_webhooks, results):
            if isinstance(result, Exception):
                logger.error(f"Webhook {webhook.url} failed: {result}")
            else:
                logger.info(f"Webhook {webhook.url} delivered successfully")

    async def _send_webhook(
        self, webhook: WebhookConfig, payload: WebhookPayload
    ) -> None:
        """
        Send a single webhook notification with retries.

        Args:
            webhook: Webhook configuration
            payload: Payload to send
        """
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Wriveted-Chatbot/1.0",
            **webhook.headers,
        }

        # Add HMAC signature if secret is provided
        if webhook.secret:
            import hashlib
            import hmac

            payload_bytes = payload.model_dump_json().encode("utf-8")
            signature = hmac.new(
                cast(str, webhook.secret).encode("utf-8"), payload_bytes, hashlib.sha256
            ).hexdigest()
            headers["X-Webhook-Signature"] = f"sha256={signature}"

        # Retry logic
        for attempt in range(webhook.retry_attempts):
            try:
                response = await self.client.post(
                    str(webhook.url),
                    json=payload.model_dump(),
                    headers=headers,
                    timeout=webhook.timeout,
                )

                # Check if request was successful
                if response.status_code < 400:
                    logger.debug(
                        f"Webhook delivered to {webhook.url} (attempt {attempt + 1})"
                    )
                    return
                else:
                    logger.warning(
                        f"Webhook {webhook.url} returned {response.status_code} (attempt {attempt + 1})"
                    )

            except httpx.TimeoutException:
                logger.warning(
                    f"Webhook {webhook.url} timed out (attempt {attempt + 1})"
                )
            except httpx.RequestError as e:
                logger.warning(
                    f"Webhook {webhook.url} request error: {e} (attempt {attempt + 1})"
                )
            except Exception as e:
                logger.error(f"Unexpected error sending webhook to {webhook.url}: {e}")
                break

            # Wait before retry (exponential backoff)
            if attempt < webhook.retry_attempts - 1:
                delay = webhook.retry_delay * (2**attempt)
                await asyncio.sleep(delay)

        raise Exception(
            f"Failed to deliver webhook to {webhook.url} after {webhook.retry_attempts} attempts"
        )


# Global webhook notifier instance
_webhook_notifier: Optional[WebhookNotifier] = None


def get_webhook_notifier() -> WebhookNotifier:
    """Get the global webhook notifier instance."""
    global _webhook_notifier
    if _webhook_notifier is None:
        _webhook_notifier = WebhookNotifier()
    return cast(WebhookNotifier, _webhook_notifier)


# Event handler to connect webhooks with flow events
async def webhook_event_handler(event: FlowEvent) -> None:
    """Event handler that sends webhook notifications for all flow events."""
    try:
        notifier = get_webhook_notifier()
        await notifier.notify_event(event)
    except Exception as e:
        logger.error(
            f"Failed to send webhook notification for event {event.event_type}: {e}"
        )


# Example webhook configurations
def setup_example_webhooks() -> None:
    """Set up example webhook configurations for testing."""
    notifier = get_webhook_notifier()

    # Example: Send all events to a monitoring service
    monitoring_webhook = WebhookConfig(
        url=HttpUrl("https://api.example.com/chatbot/events"),
        events=["*"],
        headers={"Authorization": "Bearer your-token"},
        timeout=15,
        retry_attempts=3,
    )
    notifier.add_webhook(monitoring_webhook)

    # Example: Send only completion events to analytics
    analytics_webhook = WebhookConfig(
        url=HttpUrl("https://analytics.example.com/webhook"),
        events=["session_status_changed"],
        secret="your-webhook-secret",
        timeout=10,
    )
    notifier.add_webhook(analytics_webhook)

    logger.info("Example webhooks configured")


def reset_webhook_notifier() -> None:
    """Reset the global webhook notifier instance for testing."""
    global _webhook_notifier
    if _webhook_notifier is not None:
        # Try to clean up the existing notifier
        try:
            if _webhook_notifier.session and not _webhook_notifier.session.is_closed:
                # Note: This is sync, but in tests we may not be in async context
                pass
        except Exception:
            pass
    _webhook_notifier = None
