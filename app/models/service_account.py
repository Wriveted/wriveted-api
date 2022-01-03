import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,

    String,
    JSON,
    DateTime, Boolean, ForeignKey, Enum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db import Base
from app.models.service_account_school_association import service_account_school_association_table


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
        'School',
        secondary=service_account_school_association_table,
        back_populates='service_accounts'
    )

    info = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    events = relationship("Event", back_populates="service_account")
