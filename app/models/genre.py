from sqlalchemy import (
    Column,
    Integer,
    String
)
from sqlalchemy.orm import relationship
from app.db import Base
from app.models.labelset_genre_association import labelset_genre_association_table


class Genre(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)

    name = Column(String(50), nullable=False, index=True, unique=True)
    bisac_code = Column(String(12), nullable=True, unique=True)

    labelsets = relationship(
        'LabelSet',
        secondary=labelset_genre_association_table,
        back_populates="genres"
    )

    # TODO: add a join/proxy/relationship to be able to navigate the Works associated with a Genre

    def __repr__(self):
        return f"<Genre id={self.id} - '{self.name}'>"
