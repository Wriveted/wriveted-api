from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.labelset_reading_ability_association import LabelSetReadingAbility


class ReadingAbility(Base):
    __tablename__ = "reading_abilities"  # type: ignore[assignment]

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    key: Mapped[str] = mapped_column(String(50), nullable=False, index=True, unique=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)

    labelsets = relationship(
        "LabelSet",
        secondary=LabelSetReadingAbility.__table__,
        back_populates="reading_abilities",
    )

    # TODO: add a join/proxy/relationship to be able to navigate the Works associated with a Reading Ability

    def __repr__(self) -> str:
        return f"<ReadingAbility id={self.id} - '{self.name}'>"
