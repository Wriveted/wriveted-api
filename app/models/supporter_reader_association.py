from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class SupporterReaderAssociation(Base):
    __tablename__ = "supporter_reader_association"

    supporter_id: Mapped[UUID] = mapped_column(
        "supporter_id",
        ForeignKey("users.id", name="fk_supporter_reader_assoc_supporter_id"),
        primary_key=True,
    )
    supporter: Mapped["User"] = relationship(
        "User",
        viewonly=True,
        back_populates="supportee_associations",
        foreign_keys=[supporter_id],
    )
    supporter_nickname: Mapped[str] = mapped_column(String, nullable=False)

    reader_id = mapped_column(
        "reader_id",
        ForeignKey("readers.id", name="fk_supporter_reader_assoc_reader_id"),
        primary_key=True,
    )
    reader = relationship(
        "Reader",
        viewonly=True,
        back_populates="supporter_associations",
        foreign_keys=[reader_id],
    )

    allow_phone = mapped_column(Boolean(), nullable=False, default=False)
    allow_email = mapped_column(Boolean(), nullable=False, default=True)

    is_active = mapped_column(Boolean(), nullable=False, default=True)
