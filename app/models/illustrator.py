from sqlalchemy import (
    Column,
    Computed,
    String,
    JSON,
)
from sqlalchemy.orm import relationship
from app.db import Base
from app.models.illustrator_edition_association import illustrator_edition_association_table


class Illustrator(Base):
    id = Column(String(36), primary_key=True, nullable=False)

    first_name = Column(String(200))
    last_name = Column(String(200), nullable=False)

    full_name = Column(String(400), Computed("COALESCE(first_name || ' ', '') || last_name"))

    info = Column(JSON)

    editions = relationship(
        'Edition',
        secondary=illustrator_edition_association_table,
        back_populates="illustrators"
        #cascade="all, delete-orphan"
    )
