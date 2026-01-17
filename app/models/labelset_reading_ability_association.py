from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.labelset import LabelSet
    from app.models.reading_ability import ReadingAbility


class LabelSetReadingAbility(Base):
    __tablename__ = "labelset_reading_ability_association"  # type: ignore[assignment]

    labelset_id: Mapped[int] = mapped_column(
        "labelset_id",
        ForeignKey(
            "labelsets.id", name="fk_labelset_reading_ability_association_labelset_id"
        ),
        primary_key=True,
    )
    labelset: Mapped["LabelSet"] = relationship("LabelSet", viewonly=True)

    reading_ability_id: Mapped[int] = mapped_column(
        "reading_ability_id",
        ForeignKey(
            "reading_abilities.id",
            name="fk_labelset_reading_ability_association_reading_ability_id",
        ),
        primary_key=True,
    )
    reading_ability: Mapped["ReadingAbility"] = relationship(
        "ReadingAbility", viewonly=True
    )
