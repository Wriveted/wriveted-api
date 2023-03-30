import uuid
from typing import Dict

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column

from app.models.reader import Reader
from app.models.user import UserAccountType


class PublicReader(Reader):
    """
    A concrete Reader user in public context (home/library).
    """

    __tablename__ = "public_readers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "readers.id", name="fk_public_reader_inherits_reader", ondelete="CASCADE"
        ),
        primary_key=True,
    )

    __mapper_args__ = {"polymorphic_identity": UserAccountType.PUBLIC}

    # misc
    reader_info: Mapped[Dict] = mapped_column(
        MutableDict.as_mutable(JSONB), nullable=True, default={}
    )

    def __repr__(self):
        active = "Active" if self.is_active else "Inactive"
        return f"<Public Reader {self.name} - {active}>"
