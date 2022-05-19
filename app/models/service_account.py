import enum
import uuid
from datetime import datetime

from fastapi_permissions import Allow, All
from sqlalchemy import JSON, Boolean, Column, DateTime, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship

from app.db import Base
from app.models.service_account_school_association import (
    service_account_school_association_table,
)


class ServiceAccountType(str, enum.Enum):
    BACKEND = "backend"
    LMS = "lms"
    SCHOOL = "school"
    KIOSK = "kiosk"


class ServiceAccount(Base):

    __tablename__ = "service_accounts"

    id = Column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        unique=True,
        primary_key=True,
        index=True,
        nullable=False,
    )

    name = Column(String, nullable=False)

    is_active = Column(Boolean(), default=True)
    type = Column(Enum(ServiceAccountType), nullable=False, index=True)

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

    info = Column(MutableDict.as_mutable(JSON), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
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
        ] + [
            (Allow, f"teacher:{s.id}", All) for s in self.schools]
