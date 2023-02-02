from typing import Any

from sqlalchemy.orm import DeclarativeBase, declared_attr


class Base(DeclarativeBase):
    id: Any
    __name__: str

    # Generate __tablename__ automatically
    # e.g, Class "Book" -> "books"
    # Class "Series" -> "series"
    @declared_attr
    def __tablename__(cls) -> str:
        cls_name = cls.__name__.lower()
        return cls_name if cls_name.endswith("s") else cls_name + "s"
