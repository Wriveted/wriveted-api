from sqlalchemy import JSON, Computed, Integer, String
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import mapped_column, relationship

from app.db import Base
from app.models.illustrator_edition_association import (
    illustrator_edition_association_table,
)


class Illustrator(Base):
    id = mapped_column(Integer, primary_key=True, autoincrement=True)

    first_name = mapped_column(String(200), nullable=True, index=True)
    last_name = mapped_column(String(200), nullable=False, index=True)

    name_key = mapped_column(
        String(400),
        Computed(
            "LOWER(REGEXP_REPLACE(COALESCE(first_name, '') || last_name, '\\W|_', '', 'g'))"
        ),
        unique=True,
        index=True,
    )

    info = mapped_column(MutableDict.as_mutable(JSON))

    editions = relationship(
        "Edition",
        secondary=illustrator_edition_association_table,
        back_populates="illustrators"
        # cascade="all, delete-orphan"
    )
