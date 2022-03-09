from enum import Enum as pyEnum
from sqlalchemy import Column, Enum, Integer, String
from sqlalchemy.orm import relationship
from app.db import Base
from app.models.labelset_genre_association import labelset_genre_association_table

class GenreSource(str, pyEnum):
    BISAC = "BISAC"
    BIC   = "BIC"
    THEMA = "THEMA"
    LOCSH = "LOCSH"
    HUMAN = "HUMAN"
    OTHER = "OTHER"


class Genre(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)

    name = Column(String(128), nullable=False, index=True, unique=True)
    source = Column(Enum(GenreSource), nullable=False, default=GenreSource.OTHER)

    labelsets = relationship(
        "LabelSet", secondary=labelset_genre_association_table, back_populates="genres"
    )

    # TODO: add a join/proxy/relationship to be able to navigate the Works associated with a Genre

    def __repr__(self):
        return f"<Genre id={self.id} - '{self.name}'>"
