from sqlalchemy import Boolean, ForeignKey
from app.db import Base
from sqlalchemy.orm import mapped_column, relationship


class SupporterReaderAssociation(Base):
    __tablename__ = "supporter_reader_association"

    supporter_id = mapped_column(
        "supporter_id",
        ForeignKey("users.id", name="fk_supporter_reader_assoc_supporter_id"),
        primary_key=True,
    )
    supporter = relationship(
        "User",
        viewonly=True,
        back_populates="supportee_associations",
        foreign_keys=[supporter_id],
    )

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

    is_active = mapped_column(Boolean(), nullable=False, default=True)
