import uuid
from typing import Any, Dict, Optional

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

    __tablename__ = "public_readers"  # type: ignore[assignment]

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "readers.id", name="fk_public_reader_inherits_reader", ondelete="CASCADE"
        ),
        primary_key=True,
    )

    __mapper_args__ = {"polymorphic_identity": UserAccountType.PUBLIC}

    # misc
    reader_info: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        MutableDict.as_mutable(JSONB),
        nullable=True,
        default={},  # type: ignore[arg-type]
    )

    def __repr__(self) -> str:
        active = "Active" if self.is_active else "Inactive"
        return f"<Public Reader {self.name} - {active}>"
