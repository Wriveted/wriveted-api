from typing import Annotated

from sqlalchemy import SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

str3 = Annotated[str, 3]


class Country(Base):
    __tablename__ = "countries"  # type: ignore[assignment]

    # The ISO 3166-1 Alpha-3 code for a country. E.g New Zealand is NZL, and Australia is AUS
    # https://en.wikipedia.org/wiki/List_of_ISO_3166_country_codes#Current_ISO_3166_country_codes
    id: Mapped[str3] = mapped_column(String(3), primary_key=True, index=True)

    # E.g. 61 for Australia, 64 for New Zealand
    phonecode: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    name: Mapped[str] = mapped_column(String(100), nullable=False)

    def __repr__(self) -> str:
        return f"<Country id={self.id} - '{self.name}'>"
