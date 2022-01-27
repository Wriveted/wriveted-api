from sqlalchemy import Table, Column, ForeignKey

from app.db import Base

booklist_work_association_table = Table(
    'booklist_work_association', Base.metadata,
       Column('booklist_id',
           ForeignKey('book_lists.id', name="fk_booklist_works_association_booklist_id"),
           primary_key=True),
    Column('work_id',
           ForeignKey('works.id', name="fk_booklist_works_association_work_id"),
           primary_key=True)
)
