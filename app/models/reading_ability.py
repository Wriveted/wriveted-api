from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db import Base
from app.models.labelset_reading_ability_association import LabelSetReadingAbility

class ReadingAbility(Base):
    __tablename__ = "reading_abilities"

    id = Column(Integer, primary_key=True, autoincrement=True)

    key = Column(String(50), nullable=False, index=True, unique=True)
    name = Column(String(128), nullable=False, unique=True)

    labelsets = relationship(
        "LabelSet",
        secondary=LabelSetReadingAbility.__table__,
        back_populates="reading_abilities",
    )

    # TODO: add a join/proxy/relationship to be able to navigate the Works associated with a Reading Ability

    def __repr__(self):
        return f"<ReadingAbility id={self.id} - '{self.name}'>"
