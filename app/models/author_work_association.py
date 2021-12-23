from sqlalchemy import Table, Column, ForeignKey

from app.db import Base

author_work_association_table = Table('author_work_association', Base.metadata,
    Column('work_id', ForeignKey('works.id')),
    Column('author_id', ForeignKey('authors.id'))
)