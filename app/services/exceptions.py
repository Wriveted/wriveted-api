"""
Service Layer Exceptions - Domain-specific errors for service layer.

Following the architecture principle that services should raise their own exceptions
rather than HTTP exceptions. This decouples the service layer from HTTP concerns
and makes services testable and reusable across different interfaces.
"""

from typing import List


class ServiceException(Exception):
    """Base exception for all service layer errors."""

    pass


class CMSWorkflowError(ServiceException):
    """General CMS workflow error."""

    pass


class ContentNotFoundError(CMSWorkflowError):
    """Content not found error."""

    def __init__(self, content_id: str):
        self.content_id = content_id
        super().__init__(f"Content {content_id} not found")


class ContentWorkflowError(CMSWorkflowError):
    """Content workflow operation error."""

    pass


class FlowNotFoundError(CMSWorkflowError):
    """Flow not found error."""

    def __init__(self, flow_id: str):
        self.flow_id = flow_id
        super().__init__(f"Flow {flow_id} not found")


class FlowValidationError(CMSWorkflowError):
    """Flow validation error with detailed error list."""

    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"Flow validation failed: {errors}")


class FlowPublishError(CMSWorkflowError):
    """Flow publishing error."""

    pass


class BulkOperationError(CMSWorkflowError):
    """Bulk operation error with partial results."""

    def __init__(
        self, message: str, success_count: int, error_count: int, errors: List[dict]
    ):
        self.success_count = success_count
        self.error_count = error_count
        self.errors = errors
        super().__init__(f"{message} - {success_count} succeeded, {error_count} failed")


class AnalyticsServiceError(ServiceException):
    """Analytics service specific errors."""

    pass


class ConversationServiceError(ServiceException):
    """Conversation service specific errors."""

    pass


class SessionNotFoundError(ConversationServiceError):
    """Session not found or invalid."""

    def __init__(self, session_token: str):
        self.session_token = session_token
        super().__init__(f"Session {session_token} not found or invalid")


class SessionRevisionConflictError(ConversationServiceError):
    """Session revision conflict - concurrent modification detected."""

    def __init__(self, session_id: str, expected_revision: int):
        self.session_id = session_id
        self.expected_revision = expected_revision
        super().__init__(
            f"Session {session_id} revision conflict - expected {expected_revision}"
        )


class SessionLockTimeoutError(ConversationServiceError):
    """Failed to acquire session advisory lock within timeout."""

    def __init__(self, session_id: str, timeout_seconds: int):
        self.session_id = session_id
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"Failed to acquire lock for session {session_id} within {timeout_seconds}s"
        )


class SessionConcurrencyError(ConversationServiceError):
    """Session concurrency error - too many conflicts."""

    pass


class ContentIntelligenceError(ServiceException):
    """Content intelligence service specific errors."""

    pass


class EventOutboxError(ServiceException):
    """Event outbox service specific errors."""

    pass
