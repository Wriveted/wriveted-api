"""Custom exceptions for the chat runtime."""


class ChatRuntimeError(Exception):
    """Base exception for chat runtime errors."""

    pass


class FlowNotFoundError(ChatRuntimeError):
    """Raised when a flow is not found or not available."""

    pass


class NodeNotFoundError(ChatRuntimeError):
    """Raised when a node is not found in a flow."""

    pass


class SessionNotFoundError(ChatRuntimeError):
    """Raised when a session is not found."""

    pass


class SessionInactiveError(ChatRuntimeError):
    """Raised when trying to interact with an inactive session."""

    pass


class SessionConcurrencyError(ChatRuntimeError):
    """Raised when there's a concurrency conflict in session state."""

    pass


class NodeProcessingError(ChatRuntimeError):
    """Raised when there's an error processing a node."""

    def __init__(self, message: str, node_id: str = None, node_type: str = None):
        super().__init__(message)
        self.node_id = node_id
        self.node_type = node_type


class WebhookError(NodeProcessingError):
    """Raised when a webhook call fails."""

    def __init__(self, message: str, url: str = None, status_code: int = None):
        super().__init__(message)
        self.url = url
        self.status_code = status_code


class ConditionEvaluationError(NodeProcessingError):
    """Raised when condition evaluation fails."""

    def __init__(self, message: str, condition: dict = None):
        super().__init__(message)
        self.condition = condition


class StateValidationError(ChatRuntimeError):
    """Raised when session state validation fails."""

    def __init__(self, message: str, field: str = None, value=None):
        super().__init__(message)
        self.field = field
        self.value = value
