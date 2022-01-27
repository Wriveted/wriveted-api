from sqlalchemy import Table, Column, ForeignKey
from app.db import Base

work_labelset_association = Table(
    'work_labelset_association', Base.metadata,
    Column('work_id',
           ForeignKey('works.id', name="fk_work_labelset_association_work_id"),
           primary_key=True),
    Column('genre_id',
           ForeignKey('labelsets.id', name="fk_work_labelset_association_labelset_id"),
           primary_key=True)
)
