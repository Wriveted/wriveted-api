from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.schemas import CaseInsensitiveStringEnum

if TYPE_CHECKING:
    from app.models.hue import Hue
    from app.models.labelset import LabelSet


class Ordinal(CaseInsensitiveStringEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    TERTIARY = "tertiary"


class LabelSetHue(Base):
    __tablename__ = "labelset_hue_association"  # type: ignore[assignment]

    labelset_id: Mapped[int] = mapped_column(
        "labelset_id",
        ForeignKey("labelsets.id", name="fk_labelset_hue_association_labelset_id"),
        primary_key=True,
    )
    labelset: Mapped["LabelSet"] = relationship("LabelSet", viewonly=True)

    hue_id: Mapped[int] = mapped_column(
        "hue_id",
        ForeignKey("hues.id", name="fk_labelset_hue_association_hue_id"),
        primary_key=True,
    )
    hue: Mapped["Hue"] = relationship("Hue", viewonly=True)

    ordinal: Mapped[Ordinal] = mapped_column("ordinal", Enum(Ordinal), primary_key=True)
