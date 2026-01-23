"""
Event system initialization and management.

This module provides startup and shutdown handlers for the PostgreSQL event listener
and webhook notification system.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.config import get_settings
from app.services.event_listener import get_event_listener, register_default_handlers
from app.services.webhook_notifier import get_webhook_notifier, webhook_event_handler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI lifespan context manager for event system startup and shutdown.

    This handles the PostgreSQL event listener lifecycle during application startup/shutdown.
    """
    settings = get_settings()

    # Skip event system if disabled (e.g., in tests)
    if settings.DISABLE_EVENT_LISTENER:
        logger.info("Event listener disabled via DISABLE_EVENT_LISTENER setting")
        yield
        return

    # Startup
    logger.info("Starting event system...")

    try:
        event_listener = get_event_listener()
        webhook_notifier = get_webhook_notifier()

        # Initialize webhook notifier
        await webhook_notifier.initialize()

        # Register default event handlers
        register_default_handlers(event_listener)

        # Register webhook notification handler for all events
        event_listener.register_handler("*", webhook_event_handler)

        # Start listening for PostgreSQL notifications
        await event_listener.start_listening()

        logger.info("Event system started successfully")

        yield

    except Exception as e:
        logger.error(f"Failed to start event system: {e}")
        yield

    finally:
        # Shutdown
        logger.info("Shutting down event system...")

        try:
            event_listener = get_event_listener()
            webhook_notifier = get_webhook_notifier()

            await event_listener.stop_listening()
            await event_listener.disconnect()
            await webhook_notifier.shutdown()

            logger.info("Event system shut down successfully")

        except Exception as e:
            logger.error(f"Error during event system shutdown: {e}")


def setup_event_handlers(app: FastAPI) -> None:
    """
    Set up custom event handlers for the application.

    This can be called during application initialization to register
    application-specific event handlers.
    """
    event_listener = get_event_listener()

    # Add any custom event handlers here
    # Example:
    # event_listener.register_handler("session_started", custom_session_handler)

    logger.info("Custom event handlers registered")
