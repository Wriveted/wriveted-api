from sqlalchemy import Table, Column, ForeignKey

from app.db import Base

author_work_association_table = Table('author_work_association', Base.metadata,
                                      Column('work_id',
                                             ForeignKey('works.id', name="fk_author_works_association_work_id"),
                                             primary_key=True),
                                      Column('author_id',
                                             ForeignKey('authors.id', name="fk_author_works_association_author_id"),
                                             primary_key=True)
                                      )
