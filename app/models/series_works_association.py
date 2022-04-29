from sqlalchemy import Boolean, Column, ForeignKey, Integer, Table

from app.db import Base

series_works_association_table = Table(
    "series_works_association",
    Base.metadata,
    Column(
        "series_id",
        ForeignKey("series.id", name="fk_illustrator_editions_assoc_illustrator_id"),
        primary_key=True,
    ),
    Column(
        "work_id",
        ForeignKey("works.id", name="fk_series_works_assoc_work_id"),
        primary_key=True,
    ),
    Column("primary_works", Boolean, default=True),
    Column("order_id", Integer),
)
