import enum

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
from app.models.illustrator_edition_association import illustrator_edition_association_table


class Edition(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)

    work_id = Column(
        Integer,
        ForeignKey("works.id", name="fk_editions_works"),
        index=True,
        nullable=False
    )

    # this might be a localized title
    title = Column(String(100), nullable=True)

    ISBN = Column(String(200), nullable=False, index=True)

    cover_url = Column(String(200), nullable=True)

    # Info contains stuff like edition number, language
    # Published date, published by, media (paperback/hardback/audiobook),
    # number of pages.
    info = Column(JSON)

    work = relationship('Work', back_populates='editions')

    illustrators = relationship(
        'Illustrator',
        secondary=illustrator_edition_association_table,
        back_populates='editions'
    )
