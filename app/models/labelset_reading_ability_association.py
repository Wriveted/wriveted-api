from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import relationship

from app.db import Base


class LabelSetReadingAbility(Base):
    __tablename__ = "labelset_reading_ability_association"

    labelset_id = Column(
        "labelset_id",
        ForeignKey(
            "labelsets.id", name="fk_labelset_reading_ability_association_labelset_id"
        ),
        primary_key=True,
    )
    labelset = relationship("LabelSet", viewonly=True)

    reading_ability_id = Column(
        "reading_ability_id",
        ForeignKey(
            "reading_abilities.id",
            name="fk_labelset_reading_ability_association_reading_ability_id",
        ),
        primary_key=True,
    )
