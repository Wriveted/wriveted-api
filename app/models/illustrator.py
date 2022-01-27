from sqlalchemy import (
    Column,
    Computed,
    Integer,
    String,
    JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.mutable import MutableDict
from app.db import Base
from app.models.illustrator_edition_association import illustrator_edition_association_table


class Illustrator(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)

    first_name = Column(String(200))
    last_name = Column(String(200), nullable=False)

    full_name = Column(String(400), Computed("COALESCE(first_name || ' ', '') || last_name"))

    info = Column(MutableDict.as_mutable(JSON))

    editions = relationship(
        'Edition',
        secondary=illustrator_edition_association_table,
        back_populates="illustrators"
        #cascade="all, delete-orphan"
    )
