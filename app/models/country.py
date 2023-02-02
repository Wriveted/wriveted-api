from sqlalchemy import SmallInteger, String
from sqlalchemy.orm import mapped_column

from app.db import Base


class Country(Base):
    __tablename__ = "countries"

    # The ISO 3166-1 Alpha-3 code for a country. E.g New Zealand is NZL, and Australia is AUS
    # https://en.wikipedia.org/wiki/List_of_ISO_3166_country_codes#Current_ISO_3166_country_codes
    id = mapped_column(String(3), primary_key=True, index=True)

    # Eg. 61 for Australia, 64 for New Zealand
    phonecode = mapped_column(SmallInteger, nullable=False)

    name = mapped_column(String(100), nullable=False)

    def __repr__(self):
        return f"<Country id={self.id} - '{self.name}'>"
