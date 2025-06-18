import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, List, Optional

from fastapi_permissions import All, Allow  # type: ignore[import-untyped]
from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.db import Base
from app.schemas import CaseInsensitiveStringEnum

if TYPE_CHECKING:
    from app.models.user import User


class ContentType(CaseInsensitiveStringEnum):
    JOKE = "joke"
    QUESTION = "question"
    FACT = "fact"
    QUOTE = "quote"
    MESSAGE = "message"
    PROMPT = "prompt"


class NodeType(CaseInsensitiveStringEnum):
    MESSAGE = "message"
    QUESTION = "question"
    CONDITION = "condition"
    ACTION = "action"
    WEBHOOK = "webhook"
    COMPOSITE = "composite"


class ConnectionType(CaseInsensitiveStringEnum):
    DEFAULT = "default"
    OPTION_0 = "$0"
    OPTION_1 = "$1"
    SUCCESS = "success"
    FAILURE = "failure"


class InteractionType(CaseInsensitiveStringEnum):
    MESSAGE = "message"
    INPUT = "input"
    ACTION = "action"


class SessionStatus(CaseInsensitiveStringEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class ContentStatus(CaseInsensitiveStringEnum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class CMSContent(Base):
    __tablename__ = "cms_content"  # type: ignore[assignment]

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        primary_key=True,
    )

    type: Mapped[ContentType] = mapped_column(
        Enum(ContentType, name="enum_cms_content_type"), nullable=False, index=True
    )

    content: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB),
        nullable=False,  # type: ignore[arg-type]
    )

    info: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB),  # type: ignore[arg-type]
        nullable=False,
        server_default=text("'{}'::json"),
    )

    tags: Mapped[list[str]] = mapped_column(
        MutableList.as_mutable(ARRAY(String)),
        nullable=False,
        server_default=text("'{}'::text[]"),
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true"), index=True
    )

    # Content workflow status
    status: Mapped[ContentStatus] = mapped_column(
        Enum(ContentStatus, name="enum_cms_content_status"),
        nullable=False,
        server_default=text("'draft'"),
        index=True,
    )

    # Version tracking
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", name="fk_content_created_by", ondelete="SET NULL"),
        nullable=True,
    )
    created_by_user: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[created_by], lazy="select"
    )

    # Relationships
    variants: Mapped[list["CMSContentVariant"]] = relationship(
        "CMSContentVariant", back_populates="content", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<CMSContent-{self.type} id={self.id}>"

    def __acl__(self) -> List[tuple[Any, str, str]]:
        """Defines who can do what to the content"""
        policies = [
            (Allow, "role:admin", All),
            (Allow, "role:user", "read"),
        ]
        return policies


class CMSContentVariant(Base):
    __tablename__ = "cms_content_variants"  # type: ignore[assignment]

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        primary_key=True,
    )

    content_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cms_content.id", name="fk_variant_content", ondelete="CASCADE"),
        nullable=False,
    )

    variant_key: Mapped[str] = mapped_column(String(100), nullable=False)

    variant_data: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB),
        nullable=False,  # type: ignore[arg-type]
    )

    weight: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("100")
    )

    conditions: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB),  # type: ignore[arg-type]
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    performance_data: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSON),  # type: ignore[arg-type]
        nullable=False,
        server_default=text("'{}'::json"),
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    # Relationships
    content: Mapped["CMSContent"] = relationship(
        "CMSContent", back_populates="variants"
    )

    __table_args__ = (
        UniqueConstraint("content_id", "variant_key", name="uq_content_variant_key"),
    )

    def __repr__(self) -> str:
        return f"<CMSContentVariant {self.variant_key} for {self.content_id}>"


class FlowDefinition(Base):
    __tablename__ = "flow_definitions"  # type: ignore[assignment]

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    version: Mapped[str] = mapped_column(String(50), nullable=False)

    flow_data: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB),
        nullable=False,  # type: ignore[arg-type]
    )

    entry_node_id: Mapped[str] = mapped_column(String(255), nullable=False)

    info: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB),  # type: ignore[arg-type]
        nullable=False,
        server_default=text("'{}'::json"),
    )

    is_published: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false"), index=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true"), index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", name="fk_flow_created_by", ondelete="SET NULL"),
        nullable=True,
    )

    published_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", name="fk_flow_published_by", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    created_by_user: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[created_by], lazy="select"
    )
    published_by_user: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[published_by], lazy="select"
    )

    nodes: Mapped[list["FlowNode"]] = relationship(
        "FlowNode", back_populates="flow", cascade="all, delete-orphan"
    )

    connections: Mapped[list["FlowConnection"]] = relationship(
        "FlowConnection", back_populates="flow", cascade="all, delete-orphan"
    )

    sessions: Mapped[list["ConversationSession"]] = relationship(
        "ConversationSession", back_populates="flow"
    )

    analytics: Mapped[list["ConversationAnalytics"]] = relationship(
        "ConversationAnalytics", back_populates="flow"
    )

    def __repr__(self) -> str:
        return f"<FlowDefinition {self.name} v{self.version}>"

    def __acl__(self) -> List[tuple[Any, str, str]]:
        """Defines who can do what to the flow"""
        policies = [
            (Allow, "role:admin", All),
            (Allow, "role:user", "read"),
        ]
        return policies


class FlowNode(Base):
    __tablename__ = "flow_nodes"  # type: ignore[assignment]

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        primary_key=True,
    )

    flow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("flow_definitions.id", name="fk_node_flow", ondelete="CASCADE"),
        nullable=False,
    )

    node_id: Mapped[str] = mapped_column(String(255), nullable=False)

    node_type: Mapped[NodeType] = mapped_column(
        Enum(NodeType, name="enum_flow_node_type"), nullable=False, index=True
    )

    template: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    content: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB),
        nullable=False,  # type: ignore[arg-type]
    )

    position: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB),  # type: ignore[arg-type]
        nullable=False,
        server_default=text('\'{"x": 0, "y": 0}\'::json'),
    )

    info: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB),  # type: ignore[arg-type]
        nullable=False,
        server_default=text("'{}'::json"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    flow: Mapped["FlowDefinition"] = relationship(
        "FlowDefinition", back_populates="nodes"
    )

    source_connections: Mapped[list["FlowConnection"]] = relationship(
        "FlowConnection",
        primaryjoin="and_(FlowNode.flow_id == FlowConnection.flow_id, FlowNode.node_id == FlowConnection.source_node_id)",
        back_populates="source_node",
        cascade="all, delete-orphan",
        overlaps="connections",
    )

    target_connections: Mapped[list["FlowConnection"]] = relationship(
        "FlowConnection",
        primaryjoin="and_(FlowNode.flow_id == FlowConnection.flow_id, FlowNode.node_id == FlowConnection.target_node_id)",
        back_populates="target_node",
        overlaps="connections,source_connections",
    )

    __table_args__ = (UniqueConstraint("flow_id", "node_id", name="uq_flow_node_id"),)

    def __repr__(self) -> str:
        return f"<FlowNode {self.node_id} ({self.node_type})>"


class FlowConnection(Base):
    __tablename__ = "flow_connections"  # type: ignore[assignment]

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        primary_key=True,
    )

    flow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "flow_definitions.id", name="fk_connection_flow", ondelete="CASCADE"
        ),
        nullable=False,
        index=True,
    )

    source_node_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    target_node_id: Mapped[str] = mapped_column(String(255), nullable=False)

    connection_type: Mapped[ConnectionType] = mapped_column(
        Enum(ConnectionType, name="enum_flow_connection_type"), nullable=False
    )

    conditions: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB),  # type: ignore[arg-type]
        nullable=False,
        server_default=text("'{}'::json"),
    )

    info: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB),  # type: ignore[arg-type]
        nullable=False,
        server_default=text("'{}'::json"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    # Relationships
    flow: Mapped["FlowDefinition"] = relationship(
        "FlowDefinition",
        back_populates="connections",
        overlaps="source_connections,target_connections",
    )

    source_node: Mapped["FlowNode"] = relationship(
        "FlowNode",
        primaryjoin="and_(FlowConnection.flow_id == FlowNode.flow_id, FlowConnection.source_node_id == FlowNode.node_id)",
        foreign_keys=[flow_id, source_node_id],
        back_populates="source_connections",
        overlaps="connections,flow,target_connections",
    )

    target_node: Mapped["FlowNode"] = relationship(
        "FlowNode",
        primaryjoin="and_(FlowConnection.flow_id == FlowNode.flow_id, FlowConnection.target_node_id == FlowNode.node_id)",
        foreign_keys=[flow_id, target_node_id],
        back_populates="target_connections",
        overlaps="connections,flow,source_connections,source_node",
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["flow_id", "source_node_id"],
            ["flow_nodes.flow_id", "flow_nodes.node_id"],
            name="fk_connection_source_node",
        ),
        ForeignKeyConstraint(
            ["flow_id", "target_node_id"],
            ["flow_nodes.flow_id", "flow_nodes.node_id"],
            name="fk_connection_target_node",
        ),
        UniqueConstraint(
            "flow_id",
            "source_node_id",
            "target_node_id",
            "connection_type",
            name="uq_flow_connection",
        ),
    )

    def __repr__(self) -> str:
        return f"<FlowConnection {self.source_node_id} -> {self.target_node_id} ({self.connection_type})>"


class ConversationSession(Base):
    __tablename__ = "conversation_sessions"  # type: ignore[assignment]

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        primary_key=True,
    )

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", name="fk_session_user", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    flow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("flow_definitions.id", name="fk_session_flow", ondelete="CASCADE"),
        nullable=False,
    )

    session_token: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )

    current_node_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    state: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB),  # type: ignore[arg-type]
        nullable=False,
        server_default=text("'{}'::json"),
    )

    info: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB),  # type: ignore[arg-type]
        nullable=False,
        server_default=text("'{}'::json"),
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, name="enum_conversation_session_status"),
        nullable=False,
        server_default=text("'ACTIVE'"),
        index=True,
    )

    revision: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1")
    )

    state_hash: Mapped[Optional[str]] = mapped_column(String(44), nullable=True)

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[user_id], lazy="select"
    )

    flow: Mapped["FlowDefinition"] = relationship(
        "FlowDefinition", back_populates="sessions"
    )

    history: Mapped[list["ConversationHistory"]] = relationship(
        "ConversationHistory", back_populates="session", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ConversationSession {self.session_token} ({self.status})>"


class ConversationHistory(Base):
    __tablename__ = "conversation_history"  # type: ignore[assignment]

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        primary_key=True,
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "conversation_sessions.id", name="fk_history_session", ondelete="CASCADE"
        ),
        nullable=False,
        index=True,
    )

    node_id: Mapped[str] = mapped_column(String(255), nullable=False)

    interaction_type: Mapped[InteractionType] = mapped_column(
        Enum(InteractionType, name="enum_interaction_type"), nullable=False
    )

    content: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB),
        nullable=False,  # type: ignore[arg-type]
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp(), index=True
    )

    # Relationships
    session: Mapped["ConversationSession"] = relationship(
        "ConversationSession", back_populates="history"
    )

    def __repr__(self) -> str:
        return f"<ConversationHistory {self.interaction_type} at {self.node_id}>"


class ConversationAnalytics(Base):
    __tablename__ = "conversation_analytics"  # type: ignore[assignment]

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        primary_key=True,
    )

    flow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("flow_definitions.id", name="fk_analytics_flow", ondelete="CASCADE"),
        nullable=False,
    )

    node_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    metrics: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB),
        nullable=False,  # type: ignore[arg-type]
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    # Relationships
    flow: Mapped["FlowDefinition"] = relationship(
        "FlowDefinition", back_populates="analytics"
    )

    __table_args__ = (
        UniqueConstraint(
            "flow_id", "node_id", "date", name="uq_analytics_flow_node_date"
        ),
    )

    def __repr__(self) -> str:
        return f"<ConversationAnalytics {self.flow_id} {self.node_id} {self.date}>"
