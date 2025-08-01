from typing import Any, Dict, Optional

from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Hue(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    key: Mapped[str] = mapped_column(String(50), nullable=False, index=True, unique=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)

    info: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True, default={})

    def __repr__(self) -> str:
        return f"<Hue id={self.key} - '{self.name}'>"
