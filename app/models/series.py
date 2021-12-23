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


class Series(Base):

    id = Column(String(36), primary_key=True, nullable=False)
    title = Column(String(100), nullable=False)
    info = Column(JSON)
    works = relationship('Work', back_populates="series")


