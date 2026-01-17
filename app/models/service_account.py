import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from fastapi_permissions import All, Allow  # type: ignore[import-untyped]
from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.service_account_school_association import (
    service_account_school_association_table,
)
from app.schemas import CaseInsensitiveStringEnum

if TYPE_CHECKING:
    from app.models.booklist import BookList
    from app.models.event import Event
    from app.models.school import School


class ServiceAccountType(CaseInsensitiveStringEnum):
    BACKEND = "backend"
    LMS = "lms"
    SCHOOL = "school"
    KIOSK = "kiosk"


class ServiceAccount(Base):
    __tablename__ = "service_accounts"  # type: ignore[assignment]

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        unique=True,
        primary_key=True,
        index=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean(), default=True)
    type: Mapped[ServiceAccountType] = mapped_column(
        Enum(ServiceAccountType), nullable=False, index=True
    )

    schools: Mapped[List["School"]] = relationship(
        "School",
        secondary=service_account_school_association_table,
        back_populates="service_accounts",
    )

    booklists: Mapped[List["BookList"]] = relationship(
        "BookList",
        back_populates="service_account",
        cascade="all, delete, delete-orphan",
        passive_deletes=True,
    )

    info: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        MutableDict.as_mutable(JSONB), nullable=True
    )  # type: ignore[arg-type]

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    events: Mapped[List["Event"]] = relationship(
        "Event",
        back_populates="service_account",
        lazy="dynamic",
        order_by="desc(Event.timestamp)",
    )

    def __repr__(self) -> str:
        active = "Active" if self.is_active else "Inactive"
        summary = f"{self.type} {active}"
        return f"<ServiceAccount {self.name} - {summary}>"

    async def __acl__(self) -> List[tuple[Any, str, Any]]:
        principals = [
            (Allow, "role:admin", All),
        ]

        for school in await self.awaitable_attrs.schools:
            principals.append((Allow, f"educator:{school.id}", "read"))

        return principals
