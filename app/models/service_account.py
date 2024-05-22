import uuid
from datetime import datetime

from fastapi_permissions import All, Allow
from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import mapped_column, relationship

from app.db import Base
from app.models.service_account_school_association import (
    service_account_school_association_table,
)
from app.schemas import CaseInsensitiveStringEnum


class ServiceAccountType(CaseInsensitiveStringEnum):
    BACKEND = "backend"
    LMS = "lms"
    SCHOOL = "school"
    KIOSK = "kiosk"


class ServiceAccount(Base):
    __tablename__ = "service_accounts"

    id = mapped_column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        unique=True,
        primary_key=True,
        index=True,
        nullable=False,
    )

    name = mapped_column(String, nullable=False)

    is_active = mapped_column(Boolean(), default=True)
    type = mapped_column(Enum(ServiceAccountType), nullable=False, index=True)

    schools = relationship(
        "School",
        secondary=service_account_school_association_table,
        back_populates="service_accounts",
    )

    booklists = relationship(
        "BookList",
        back_populates="service_account",
        cascade="all, delete, delete-orphan",
        passive_deletes=True,
    )

    info = mapped_column(MutableDict.as_mutable(JSONB), nullable=True)

    created_at = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    events = relationship(
        "Event",
        back_populates="service_account",
        lazy="dynamic",
        order_by="desc(Event.timestamp)",
    )

    def __repr__(self):
        active = "Active" if self.is_active else "Inactive"
        summary = f"{self.type} {active}"
        return f"<ServiceAccount {self.name} - {summary}>"

    def __acl__(self):
        return [
            (Allow, "role:admin", All),
        ]
        # + [(Allow, f"educator:{s.id}", All) for s in self.schools]
