from sqlalchemy import ForeignKey, Table
from sqlalchemy.orm import mapped_column

from app.db import Base

author_work_association_table = Table(
    "author_work_association",
    Base.metadata,
    mapped_column(
        "work_id",
        ForeignKey("works.id", name="fk_author_works_association_work_id"),
        primary_key=True,
    ),
    mapped_column(
        "author_id",
        ForeignKey("authors.id", name="fk_author_works_association_author_id"),
        primary_key=True,
    ),
)
