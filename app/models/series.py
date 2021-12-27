from sqlalchemy import (
    Column,
    Integer,
    String,
    JSON,
)
from sqlalchemy.orm import relationship
from app.db import Base
from app.models.series_works_association import series_works_association_table


class Series(Base):

    id = Column(Integer, primary_key=True, autoincrement=True)

    title = Column(String(100), nullable=False)

    # description etc
    info = Column(JSON)

    # TODO order this relationship by the secondary table
    works = relationship(
        'Work',
        secondary=series_works_association_table,
        back_populates="series"
    )
