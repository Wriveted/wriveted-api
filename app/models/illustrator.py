from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Computed, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.illustrator_edition_association import (
    illustrator_edition_association_table,
)

if TYPE_CHECKING:
    from app.models.edition import Edition


class Illustrator(Base):
    __tablename__ = "illustrators"  # type: ignore[assignment]

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    first_name: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, index=True
    )
    last_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)

    name_key: Mapped[str] = mapped_column(
        String(400),
        Computed(
            "LOWER(REGEXP_REPLACE(COALESCE(first_name, '') || last_name, '\\W|_', '', 'g'))"
        ),
        unique=True,
        index=True,
    )

    info: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        MutableDict.as_mutable(JSONB)
    )  # type: ignore[arg-type]

    editions: Mapped[List["Edition"]] = relationship(
        "Edition",
        secondary=illustrator_edition_association_table,
        back_populates="illustrators",
        # cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Illustrator id={self.id} - '{self.first_name} {self.last_name}'>"

    def __str__(self) -> str:
        if self.first_name is not None:
            return f"{self.first_name} {self.last_name}"
        else:
            return self.last_name
