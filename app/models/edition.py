from sqlalchemy import (
    Column,
    Computed,
    ForeignKey,
    Integer,
    String,
    JSON,
)
from sqlalchemy.orm import relationship
from app.db import Base
from app.models.illustrator_edition_association import illustrator_edition_association_table


class Edition(Base):
    id = Column(String(36), primary_key=True, nullable=False, unique=True)
    work_id = Column(String(36), ForeignKey("works.id", name="FK_Editions_Works"), primary_key=True, nullable=False)
    #ordering_id = Column(Integer(), primary_key=True, autoincrement=True)
    ISBN = Column(String(200), nullable=False)
    cover_url = Column(String(200), nullable=False)
    info = Column(JSON)

    work = relationship('Work', back_populates='editions')

    illustrators = relationship(
        'Illustrator',
        secondary=illustrator_edition_association_table,
        back_populates='editions'
    )
