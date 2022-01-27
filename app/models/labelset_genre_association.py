from sqlalchemy import Table, Column, ForeignKey
from app.db import Base

labelset_genre_association_table = Table(
    'labelset_genre_association', Base.metadata,
    Column('labelset_id',
           ForeignKey('labelsets.id', name="fk_labelset_genre_association_labelset_id"),
           primary_key=True),
    Column('genre_id',
           ForeignKey('genres.id', name="fk_labelset_genre_association_genre_id"),
           primary_key=True)
)
