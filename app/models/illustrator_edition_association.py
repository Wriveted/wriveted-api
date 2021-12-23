from sqlalchemy import Table, Column, ForeignKey, String, UniqueConstraint

from app.db import Base

illustrator_edition_association_table = Table(
    'illustrator_edition_association',
    Base.metadata,
    # Note editions have composite primary keys
    Column('edition_id', String(36), ForeignKey('editions.id')),
    Column('work_id', String(36), ForeignKey('works.id')),

    Column('illustrator_id', String(36), ForeignKey('illustrators.id')),
)