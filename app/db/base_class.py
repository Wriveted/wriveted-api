from typing import Any

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, declared_attr

# SQLAlchemy naming conventions for constraints and indexes
# This ensures consistent, predictable names across all migrations
# See: https://alembic.sqlalchemy.org/en/latest/naming.html
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(AsyncAttrs, DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    id: Any
    __name__: str

    # Generate __tablename__ automatically
    # e.g, Class "Book" -> "books"
    # Class "Series" -> "series"
    @declared_attr
    def __tablename__(cls) -> str:
        cls_name = cls.__name__.lower()
        return cls_name if cls_name.endswith("s") else cls_name + "s"
