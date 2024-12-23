import uuid
from datetime import datetime
from typing import Optional

from fastapi_permissions import All, Allow
from sqlalchemy import DateTime, Enum, ForeignKey, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.schemas import CaseInsensitiveStringEnum


class ContentType(CaseInsensitiveStringEnum):
    JOKE = "joke"
    QUESTION = "question"
    FACT = "fact"
    QUOTE = "quote"


class CMSContent(Base):
    __tablename__ = "cms_content"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        primary_key=True,
    )

    type: Mapped[ContentType] = mapped_column(
        Enum(ContentType, name="enum_cms_content_type"), nullable=False, index=True
    )

    content: Mapped[Optional[dict]] = mapped_column(MutableDict.as_mutable(JSONB))

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

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", name="fk_content_user", ondelete="CASCADE"),
        nullable=True,
    )
    user: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[user_id], lazy="joined"
    )

    def __repr__(self):
        return f"<CMSContent-{self.type} id={self.id}>"

    def __acl__(self):
        """
        Defines who can do what to the content
        """

        policies = [
            (Allow, "role:admin", All),
            (Allow, "role:user", "read"),
        ]

        return policies
