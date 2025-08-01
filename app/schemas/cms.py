from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import UUID4, BaseModel, ConfigDict, Field, field_validator

from app.models.cms import (
    ConnectionType,
    ContentStatus,
    ContentType,
    InteractionType,
    NodeType,
    SessionStatus,
)
from app.schemas.pagination import PaginatedResponse


# Content Schemas
class ContentCreate(BaseModel):
    type: ContentType
    content: Dict[str, Any]
    info: Optional[Dict[str, Any]] = {}
    tags: Optional[List[str]] = []
    is_active: Optional[bool] = True
    status: Optional[ContentStatus] = ContentStatus.DRAFT

    @field_validator("content")
    @classmethod
    def validate_content_not_empty(cls, v):
        if not v:
            raise ValueError("Content cannot be empty")
        return v


class ContentUpdate(BaseModel):
    type: Optional[ContentType] = None
    content: Optional[Dict[str, Any]] = None
    info: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None
    status: Optional[ContentStatus] = None


class ContentBrief(BaseModel):
    id: UUID4
    type: ContentType
    tags: List[str]
    is_active: bool
    status: ContentStatus
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ContentDetail(ContentBrief):
    content: Dict[str, Any]
    info: Dict[str, Any]
    created_by: Optional[UUID4] = None


class ContentResponse(PaginatedResponse):
    data: List[ContentDetail]


# Content Variant Schemas
class ContentVariantCreate(BaseModel):
    variant_key: str = Field(..., max_length=100)
    variant_data: Dict[str, Any]
    weight: Optional[int] = 100
    conditions: Optional[Dict[str, Any]] = {}
    is_active: Optional[bool] = True


class ContentVariantUpdate(BaseModel):
    variant_data: Optional[Dict[str, Any]] = None
    weight: Optional[int] = None
    conditions: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class ContentVariantDetail(BaseModel):
    id: UUID4
    content_id: UUID4
    variant_key: str
    variant_data: Dict[str, Any]
    weight: int
    conditions: Dict[str, Any]
    performance_data: Dict[str, Any]
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ContentVariantResponse(PaginatedResponse):
    data: List[ContentVariantDetail]


class VariantPerformanceUpdate(BaseModel):
    impressions: Optional[int] = None
    engagements: Optional[int] = None
    conversions: Optional[int] = None


# Flow Schemas
class FlowCreate(BaseModel):
    name: str = Field(
        ..., min_length=1, max_length=255, description="Flow name cannot be empty"
    )
    description: Optional[str] = None
    version: str = Field(..., max_length=50)
    flow_data: Dict[str, Any]
    entry_node_id: str = Field(..., max_length=255)
    info: Optional[Dict[str, Any]] = {}


class FlowUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    version: Optional[str] = Field(None, max_length=50)
    flow_data: Optional[Dict[str, Any]] = None
    entry_node_id: Optional[str] = Field(None, max_length=255)
    info: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class FlowBrief(BaseModel):
    id: UUID4
    name: str
    version: str
    is_published: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class FlowDetail(FlowBrief):
    description: Optional[str] = None
    flow_data: Dict[str, Any]
    entry_node_id: str
    info: Dict[str, Any]
    created_by: Optional[UUID4] = None
    published_by: Optional[UUID4] = None


class FlowResponse(PaginatedResponse):
    data: List[FlowDetail]


class FlowPublishRequest(BaseModel):
    publish: bool = True


class FlowCloneRequest(BaseModel):
    name: str = Field(..., max_length=255)
    version: str = Field(..., max_length=50)


# Flow Node Schemas
class NodeCreate(BaseModel):
    node_id: str = Field(..., max_length=255)
    node_type: NodeType
    template: Optional[str] = Field(None, max_length=100)
    content: Dict[str, Any]
    position: Optional[Dict[str, Any]] = {"x": 0, "y": 0}
    info: Optional[Dict[str, Any]] = {}


class NodeUpdate(BaseModel):
    node_type: Optional[NodeType] = None
    template: Optional[str] = Field(None, max_length=100)
    content: Optional[Dict[str, Any]] = None
    position: Optional[Dict[str, Any]] = None
    info: Optional[Dict[str, Any]] = None


class NodeDetail(BaseModel):
    id: UUID4
    flow_id: UUID4
    node_id: str
    node_type: NodeType
    template: Optional[str] = None
    content: Dict[str, Any]
    position: Dict[str, Any]
    info: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NodeResponse(PaginatedResponse):
    data: List[NodeDetail]


class NodePositionUpdate(BaseModel):
    positions: Dict[str, Dict[str, Any]]


# Flow Connection Schemas
class ConnectionCreate(BaseModel):
    source_node_id: str = Field(..., max_length=255)
    target_node_id: str = Field(..., max_length=255)
    connection_type: ConnectionType
    conditions: Optional[Dict[str, Any]] = {}
    info: Optional[Dict[str, Any]] = {}


class ConnectionDetail(BaseModel):
    id: UUID4
    flow_id: UUID4
    source_node_id: str
    target_node_id: str
    connection_type: ConnectionType
    conditions: Dict[str, Any]
    info: Dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConnectionResponse(PaginatedResponse):
    data: List[ConnectionDetail]


# Conversation Session Schemas
class SessionCreate(BaseModel):
    flow_id: UUID4
    user_id: Optional[UUID4] = None
    initial_state: Optional[Dict[str, Any]] = {}


class SessionDetail(BaseModel):
    id: UUID4
    user_id: Optional[UUID4] = None
    flow_id: UUID4
    session_token: str
    current_node_id: Optional[str] = None
    state: Dict[str, Any]
    info: Dict[str, Any]
    started_at: datetime
    last_activity_at: datetime
    ended_at: Optional[datetime] = None
    status: SessionStatus
    revision: int
    state_hash: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SessionStartResponse(BaseModel):
    session_id: UUID4
    session_token: str
    next_node: Optional[Dict[str, Any]] = None


class SessionStateUpdate(BaseModel):
    updates: Dict[str, Any]
    expected_revision: Optional[int] = None


# Conversation Interaction Schemas
class InteractionCreate(BaseModel):
    input: str
    input_type: str = Field(..., pattern="^(text|button|file)$")


class InteractionResponse(BaseModel):
    messages: List[Dict[str, Any]]
    input_request: Optional[Dict[str, Any]] = None
    session_ended: bool = False


class ConversationHistoryDetail(BaseModel):
    id: UUID4
    session_id: UUID4
    node_id: str
    interaction_type: InteractionType
    content: Dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationHistoryResponse(PaginatedResponse):
    data: List[ConversationHistoryDetail]


# Analytics Schemas
class AnalyticsGranularity(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class AnalyticsDetail(BaseModel):
    id: UUID4
    flow_id: UUID4
    node_id: Optional[str] = None
    date: date
    metrics: Dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnalyticsResponse(PaginatedResponse):
    data: List[AnalyticsDetail]


class FunnelAnalyticsRequest(BaseModel):
    start_node: str
    end_node: str


class FunnelAnalyticsResponse(BaseModel):
    funnel_steps: List[Dict[str, Any]]
    conversion_rate: float
    total_sessions: int


class AnalyticsExportRequest(BaseModel):
    flow_id: UUID4
    format: str = Field(..., pattern="^(csv|json)$")


# Bulk Operations Schemas
class BulkOperation(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class BulkContentRequest(BaseModel):
    operation: BulkOperation
    items: List[Union[ContentCreate, ContentUpdate, UUID4]]


class BulkContentResponse(BaseModel):
    success_count: int
    error_count: int
    errors: List[Dict[str, Any]] = []


# Content Workflow Schemas
class ContentStatusUpdate(BaseModel):
    status: ContentStatus
    comment: Optional[str] = None


# Webhook Schemas
class WebhookCreate(BaseModel):
    url: str = Field(..., pattern="^https?://.*")
    events: List[str]
    headers: Optional[Dict[str, str]] = {}
    is_active: Optional[bool] = True


class WebhookUpdate(BaseModel):
    url: Optional[str] = Field(None, pattern="^https?://.*")
    events: Optional[List[str]] = None
    headers: Optional[Dict[str, str]] = None
    is_active: Optional[bool] = None


class WebhookDetail(BaseModel):
    id: UUID4
    url: str
    events: List[str]
    headers: Dict[str, str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WebhookResponse(PaginatedResponse):
    data: List[WebhookDetail]


class WebhookTestResponse(BaseModel):
    success: bool
    status_code: Optional[int] = None
    response_time: Optional[float] = None
    error: Optional[str] = None


# Content Type Specific Schemas
class JokeContent(BaseModel):
    setup: str
    punchline: str
    category: Optional[str] = None
    age_group: Optional[List[str]] = []


class FactContent(BaseModel):
    text: str
    source: Optional[str] = None
    topic: Optional[str] = None
    difficulty: Optional[str] = None


class MessageContent(BaseModel):
    text: str
    rich_text: Optional[str] = None
    typing_delay: Optional[float] = None
    media: Optional[Dict[str, Any]] = None


class QuestionContent(BaseModel):
    text: str
    options: Optional[List[Dict[str, str]]] = []
    input_type: Optional[str] = "text"


class QuoteContent(BaseModel):
    text: str
    author: Optional[str] = None
    source: Optional[str] = None


class PromptContent(BaseModel):
    text: str
    context: Optional[str] = None
    expected_response_type: Optional[str] = None


# Node Content Type Schemas
class MessageNodeContent(BaseModel):
    messages: List[Dict[str, Any]]
    typing_indicator: Optional[bool] = True


class QuestionNodeContent(BaseModel):
    question: Dict[str, Any]
    input_type: str
    options: Optional[List[Dict[str, str]]] = []
    validation: Optional[Dict[str, Any]] = {}


class ConditionNodeContent(BaseModel):
    conditions: List[Dict[str, Any]]


class ActionNodeContent(BaseModel):
    action: str
    params: Dict[str, Any]


class WebhookNodeContent(BaseModel):
    url: str
    method: str = "POST"
    headers: Optional[Dict[str, str]] = {}
    payload: Optional[Dict[str, Any]] = {}
