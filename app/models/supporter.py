import uuid
from typing import Dict, Optional

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import User, UserAccountType


class Supporter(User):
    """
    A user who supports and encourages reader(s).
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_supporter_inherits_user", ondelete="CASCADE"),
        primary_key=True,
    )

    __mapper_args__ = {"polymorphic_identity": UserAccountType.SUPPORTER}

    # misc
    supporter_info: Mapped[Optional[Dict]] = mapped_column(
        MutableDict.as_mutable(JSONB), nullable=True, default={}  # type: ignore[arg-type]
    )

    def __repr__(self) -> str:
        active = "Active" if self.is_active else "Inactive"
        return f"<Supporter {self.name} - {active}>"
