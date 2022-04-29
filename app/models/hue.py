from sqlalchemy import Column, Integer, String

from app.db import Base


class Hue(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)

    key = Column(String(50), nullable=False, index=True, unique=True)
    name = Column(String(128), nullable=False, unique=True)

    # TODO: add a join/proxy/relationship to be able to navigate the Works associated with a Hue

    def __repr__(self):
        return f"<Hue id={self.key} - '{self.name}'>"
