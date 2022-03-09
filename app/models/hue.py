from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db import Base
from app.models import LabelSetHue


class Hue(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    key = Column(String(50), nullable=False, index=True, unique=True)
    name = Column(String(50), nullable=False, unique=True)

    labelsets = relationship(
        "LabelSet", secondary=LabelSetHue.__table__, back_populates="hues"
    )

    # TODO: add a join/proxy/relationship to be able to navigate the Works associated with a Hue

    def __repr__(self):
        return f"<Hue id={self.key} - '{self.name}'>"
