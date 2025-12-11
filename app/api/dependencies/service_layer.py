"""
Service layer dependency injection and error handling.

This module provides centralized error handling for service layer operations,
converting domain exceptions to appropriate HTTP responses.
"""

from functools import wraps
from typing import Any, Callable, TypeVar

from fastapi import HTTPException
from structlog import get_logger

from app.services.exceptions import (
    CMSWorkflowError,
    ContentNotFoundError,
    ContentWorkflowError,
    FlowNotFoundError,
    FlowValidationError,
)

logger = get_logger()

F = TypeVar("F", bound=Callable[..., Any])


def handle_service_errors(func: F) -> F:
    """
    Decorator to handle service layer exceptions and convert them to HTTP responses.

    This eliminates the need for duplicated try/catch blocks in API endpoints.

    Usage:
        @handle_service_errors
        async def my_endpoint():
            return await service.do_something()
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except FlowNotFoundError as e:
            logger.warning("Flow not found", error=str(e))
            raise HTTPException(status_code=404, detail=f"Flow not found: {str(e)}")
        except ContentNotFoundError as e:
            logger.warning("Content not found", error=str(e))
            raise HTTPException(status_code=404, detail=f"Content not found: {str(e)}")
        except FlowValidationError as e:
            logger.warning("Flow validation failed", errors=e.validation_errors)
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Flow validation failed",
                    "validation_errors": e.validation_errors,
                },
            )
        except ContentWorkflowError as e:
            logger.warning("Content workflow error", error=str(e))
            raise HTTPException(
                status_code=400, detail=f"Content workflow error: {str(e)}"
            )
        except CMSWorkflowError as e:
            logger.warning("CMS workflow error", error=str(e))
            raise HTTPException(status_code=500, detail=f"CMS workflow error: {str(e)}")
        except ValueError as e:
            logger.warning("Invalid input", error=str(e))
            raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")
        except Exception as e:
            logger.error("Unexpected service error", error=str(e), exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred while processing your request",
            )

    return wrapper


def get_analytics_service():
    """Dependency to get AnalyticsService instance."""
    from app.services.analytics import AnalyticsService

    return AnalyticsService()


def get_cms_workflow_service():
    """Dependency to get CMSWorkflowService instance."""
    from app.services.cms_workflow import CMSWorkflowService

    return CMSWorkflowService()
