from sqlalchemy import JSON, Column, Computed, Integer, String
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship

from app.db import Base
from app.models.illustrator_edition_association import (
    illustrator_edition_association_table,
)


class Illustrator(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)

    first_name = Column(String(200), nullable=True, index=True)
    last_name = Column(String(200), nullable=False, index=True)

    name_key = Column(
        String(400),
        Computed(
            "LOWER(REGEXP_REPLACE(COALESCE(first_name, '') || last_name, '\\W|_', '', 'g'))"
        ),
        unique=True,
        index=True,
    )

    info = Column(MutableDict.as_mutable(JSON))

    editions = relationship(
        "Edition",
        secondary=illustrator_edition_association_table,
        back_populates="illustrators"
        # cascade="all, delete-orphan"
    )
