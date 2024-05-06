from sqlalchemy import Column, Integer, Table

from app.db.base_class import Base

search_view_v1 = Table(
    "work_collection_frequency",
    Base.metadata,
    Column("work_id", Integer, primary_key=True),
    Column("series_id", Integer),
)
