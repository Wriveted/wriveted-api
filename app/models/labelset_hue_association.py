from sqlalchemy import Column, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.db import Base
import enum


class Ordinal(str, enum.Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    TERTIARY = "tertiary"

class LabelSetHue(Base):
    __tablename__ = "labelset_hue_association"

    labelset_id = Column(
        "labelset_id",
        ForeignKey("labelsets.id", name="fk_labelset_hue_association_labelset_id"),
        primary_key=True,
    )
    labelset = relationship("LabelSet", lazy="joined")

    hue_id = Column(
        "hue_id",
        ForeignKey("hues.id", name="fk_labelset_hue_association_hue_id"),
        primary_key=True,
    )

    ordinal = Column("ordinal", Enum(Ordinal), primary_key=True)