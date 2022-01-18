from sqlalchemy import (
    Column,
    Integer,
    String
)
from sqlalchemy.orm import relationship
from app.db import Base
from app.models.labelset_hue_association import labelset_hue_association_table


class Hue(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)

    name = Column(String(50), nullable=False, index=True, unique=True)

    labelsets = relationship(
        'LabelSet',
        secondary=labelset_hue_association_table,
        back_populates="hues"
    )

    # TODO: add a join/proxy/relationship to be able to navigate the Works associated with a Hue

    def __repr__(self):
        return f"<Hue id={self.id} - '{self.name}'>"
