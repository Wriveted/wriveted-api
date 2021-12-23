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
from app.models.author_work_association import author_work_association_table


class Author(Base):
    id = Column(String(36), primary_key=True, nullable=False)

    first_name = Column(String(200))
    last_name = Column(String(200), nullable=False)

    full_name = Column(String(400), Computed("COALESCE(first_name || ' ', '') || last_name"))

    info = Column(JSON)

    books = relationship(
        'Work',
        secondary=author_work_association_table,
        back_populates="authors"
        #cascade="all, delete-orphan"
    )
