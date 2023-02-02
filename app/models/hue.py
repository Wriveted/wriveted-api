from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column

from app.db import Base


class Hue(Base):
    id = mapped_column(Integer, primary_key=True, autoincrement=True)

    key = mapped_column(String(50), nullable=False, index=True, unique=True)
    name = mapped_column(String(128), nullable=False, unique=True)

    info = mapped_column(JSONB, nullable=True, default={})

    def __repr__(self):
        return f"<Hue id={self.key} - '{self.name}'>"
