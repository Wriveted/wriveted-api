from sqlalchemy import (
    Column,
    Computed,
    Integer,
    String,
    JSON, select, func, and_,
)
from sqlalchemy.orm import relationship, column_property
from app.db import Base
from app.models.hue_work_association import hue_work_association_table
from app.models.work import Work


class Hue(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)

    name = Column(String(50), nullable=False, index=True, unique=True)

    books = relationship(
        'Work',
        secondary=hue_work_association_table,
        back_populates="hues"
    )

    def __repr__(self):
        return f"<Hue id={self.id} - '{self.name}'>"
