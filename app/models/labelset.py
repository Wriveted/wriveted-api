import enum

from sqlalchemy import (
    Enum,
    JSON,
    ForeignKey,
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    func,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.mutable import MutableDict
from app.db import Base
from app.models.author_work_association import author_work_association_table
from app.models.series_works_association import series_works_association_table
from app.models.labelset_hue_association import labelset_hue_association_table
from app.models.labelset_genre_association import labelset_genre_association_table


class ReadingAbility(str, enum.Enum):
    SPOT = "Where's Spot"
    CAT_HAT = "Cat in the Hat"
    TREEHOUSE = "The 13-Storey Treehouse"
    CHARLIE_CHOCOLATE = "Charlie and the Chocolate Factory"
    HARRY_POTTER = "Harry Potter and the Philosopher's Stone"


class DoeCode(str, enum.Enum):
    DOE_2G = "2G"
    DOE_2H = "2H"
    DOE_2I = "2I"
    DOE_2J = "2J"
    DOE_2K = "2K"
    DOE_2L = "2L"
    DOE_3G = "3G"
    DOE_3H = "3H"
    DOE_3I = "3I"
    DOE_3J = "3J"
    DOE_3K = "3K"
    DOE_3L = "3L"
    DOE_4G = "4G"
    DOE_4H = "4H"
    DOE_4I = "4I"
    DOE_4J = "4J"
    DOE_4K = "4K"
    DOE_4L = "4L"


# an abstraction of the "label" related properties of a Work, which are likely to be human-provided
class LabelSet(Base):

    id = Column(Integer, primary_key=True, autoincrement=True)

    work_id = Column(
        ForeignKey("works.id", name="fk_labelset_work"), nullable=True, index=True
    )
    work = relationship("Work", back_populates="labelset")

    # Handle Multiple Hues via a secondary association table,
    # discerned via an 'ordinal' (primary/secondary/tertiary)
    hues = relationship(
        "Hue",
        secondary=labelset_hue_association_table,
        back_populates="labelsets",
        lazy="selectin",
        order_by="desc(labelset_hue_association.c.ordinal)",
    )

    genres = relationship(
        "Genre",
        secondary=labelset_genre_association_table,
        back_populates="labelsets",
        lazy="selectin",
    )

    reading_ability = Column(Enum(ReadingAbility), nullable=True)

    doe_code = Column(Enum(DoeCode), nullable=True)

    # likely to be more robust than tagged concepts of a range i.e. "3to6" and "5to7"
    min_age = Column(Integer, nullable=True)
    max_age = Column(Integer, nullable=True)

    # e.g. 1000L
    lexile = Column(String(length=5), nullable=True)

    # service accounts and users could potentially label works
    labelled_by_user_id = Column(
        ForeignKey("users.id", name="fk_labeller-user_labelset"), nullable=True
    )
    labelled_by_sa_id = Column(
        ForeignKey("service_accounts.id", name="fk_labeller-sa_labelset"), nullable=True
    )

    info = Column(MutableDict.as_mutable(JSON))

    created_at = Column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at = Column(DateTime, nullable=False, onupdate=func.current_timestamp())

    checked = Column(Boolean(), default=False)

    def __repr__(self):
        return f"<LabelSet id={self.id} - '{self.work.title (self.work.isbn)}'>"
