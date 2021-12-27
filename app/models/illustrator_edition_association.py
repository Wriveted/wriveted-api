from sqlalchemy import Table, Column, ForeignKey, String, UniqueConstraint, Integer

from app.db import Base

illustrator_edition_association_table = Table(
    'illustrator_edition_association',
    Base.metadata,

    Column('edition_id', ForeignKey('editions.id', name="fk_illustrator_editions_assoc_edition_id"), primary_key=True),
    Column('illustrator_id', ForeignKey('illustrators.id', name="fk_illustrator_editions_assoc_illustrator_id"),
           primary_key=True),
)
