from typing import Any

from sqlalchemy.ext.declarative import as_declarative, declared_attr


@as_declarative()
class Base:
    id: Any
    __name__: str

    # Generate __tablename__ automatically
    # eg. Class "Book" -> "books"
    # Class "Series" -> "series"
    @declared_attr
    def __tablename__(cls) -> str:
        cls_name = cls.__name__.lower()
        return cls_name if cls_name.endswith('s') else cls_name + 's'
