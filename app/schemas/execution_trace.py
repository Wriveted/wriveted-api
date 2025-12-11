"""Pydantic schemas for execution trace data."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

# Execution detail schemas per node type


class ConditionEval(BaseModel):
    """Single condition evaluation result."""

    index: int
    expression: str
    result: bool
    error: Optional[str] = None


class ConditionExecutionDetails(BaseModel):
    """Execution details for CONDITION nodes."""

    type: Literal["condition"] = "condition"
    conditions_evaluated: List[ConditionEval]
    matched_condition_index: Optional[int] = None
    connection_taken: str


class ScriptExecutionDetails(BaseModel):
    """Execution details for SCRIPT nodes."""

    type: Literal["script"] = "script"
    language: Literal["javascript", "typescript"]
    code_preview: str = Field(max_length=500)
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    console_logs: List[str] = Field(default_factory=list)
    error: Optional[str] = None
    execution_time_ms: Optional[int] = None


class QuestionExecutionDetails(BaseModel):
    """Execution details for QUESTION nodes."""

    type: Literal["question"] = "question"
    question_text: str
    rendered_question: str
    options: Optional[List[str]] = None
    user_response: Optional[str] = None
    response_time_ms: Optional[int] = None
    input_type: str = "text"


class MessageExecutionDetails(BaseModel):
    """Execution details for MESSAGE nodes."""

    type: Literal["message"] = "message"
    message_template: str
    rendered_message: str
    media_urls: List[str] = Field(default_factory=list)


class ActionExecutionDetails(BaseModel):
    """Execution details for ACTION nodes."""

    type: Literal["action"] = "action"
    action_type: str
    actions_executed: List[Dict[str, Any]]
    variables_changed: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class WebhookExecutionDetails(BaseModel):
    """Execution details for WEBHOOK nodes."""

    type: Literal["webhook"] = "webhook"
    url: str
    method: str
    request_headers: Dict[str, str] = Field(default_factory=dict)
    response_status: Optional[int] = None
    response_body: Optional[Dict[str, Any]] = None
    duration_ms: Optional[int] = None
    error: Optional[str] = None


class StartExecutionDetails(BaseModel):
    """Execution details for START nodes."""

    type: Literal["start"] = "start"
    entry_point: bool = True
    initial_context: Dict[str, Any] = Field(default_factory=dict)


class CompositeExecutionDetails(BaseModel):
    """Execution details for COMPOSITE nodes."""

    type: Literal["composite"] = "composite"
    composite_flow_id: Optional[str] = None
    sub_steps: int = 0


# Union type for all execution details
ExecutionDetails = Union[
    ConditionExecutionDetails,
    ScriptExecutionDetails,
    QuestionExecutionDetails,
    MessageExecutionDetails,
    ActionExecutionDetails,
    WebhookExecutionDetails,
    StartExecutionDetails,
    CompositeExecutionDetails,
]


# API Response schemas


class ExecutionStepResponse(BaseModel):
    """Single execution step in trace response."""

    id: UUID
    step_number: int
    node_id: str
    node_type: str
    state_before: Dict[str, Any]
    state_after: Dict[str, Any]
    execution_details: Dict[str, Any]
    connection_type: Optional[str] = None
    next_node_id: Optional[str] = None
    duration_ms: Optional[int] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None


class SessionSummary(BaseModel):
    """Summary of a session for list views."""

    id: UUID
    session_token: str
    user_id: Optional[UUID] = None
    flow_id: UUID
    status: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    total_steps: int
    has_errors: bool
    error_count: int = 0
    path_summary: List[str]


class SessionTraceResponse(BaseModel):
    """Full session trace response."""

    session: Dict[str, Any]
    steps: List[ExecutionStepResponse]
    total_steps: int
    total_duration_ms: int


class SessionListResponse(BaseModel):
    """Paginated list of sessions."""

    items: List[SessionSummary]
    total: int
    limit: int
    offset: int


class TracingConfigRequest(BaseModel):
    """Request to configure tracing for a flow."""

    enabled: bool
    level: Literal["minimal", "standard", "verbose"] = "standard"
    sample_rate: float = Field(default=1.0, ge=0.0, le=1.0)


class TracingConfigResponse(BaseModel):
    """Response with current tracing configuration."""

    flow_id: UUID
    enabled: bool
    level: str
    sample_rate: float


class PathAnalyticsResponse(BaseModel):
    """Aggregated path analytics for a flow."""

    flow_id: UUID
    total_sessions: int
    paths: List[Dict[str, Any]]
    drop_off_points: List[Dict[str, Any]]


class TraceStorageStats(BaseModel):
    """Storage statistics for traces."""

    total_traces: int
    table_size: str
    oldest_trace: Optional[datetime] = None
    newest_trace: Optional[datetime] = None
