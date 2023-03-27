from sqlalchemy import Enum, ForeignKey
from sqlalchemy.orm import mapped_column, relationship

from app.db import Base
from app.schemas import CaseInsensitiveStringEnum


class Ordinal(CaseInsensitiveStringEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    TERTIARY = "tertiary"


class LabelSetHue(Base):
    __tablename__ = "labelset_hue_association"

    labelset_id = mapped_column(
        "labelset_id",
        ForeignKey("labelsets.id", name="fk_labelset_hue_association_labelset_id"),
        primary_key=True,
    )
    labelset = relationship("LabelSet", viewonly=True)

    hue_id = mapped_column(
        "hue_id",
        ForeignKey("hues.id", name="fk_labelset_hue_association_hue_id"),
        primary_key=True,
    )

    ordinal = mapped_column("ordinal", Enum(Ordinal), primary_key=True)
