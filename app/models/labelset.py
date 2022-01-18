import enum

from sqlalchemy import (
    Enum,
    ForeignKey,
    Column,
    Integer,
    String,
    Boolean,
    DateTime
)
from sqlalchemy.orm import relationship

from app.db import Base
from app.models.author_work_association import author_work_association_table
from app.models.series_works_association import series_works_association_table
from app.models.labelset_hue_association import labelset_hue_association_table


class ReadingAbility(str, enum.Enum):
    SPOT              = "Where's Spot"
    CAT_HAT           = "Cat in the Hat"
    TREEHOUSE         = "The 13-Storey Treehouse"
    CHARLIE_CHOCOLATE = "Charlie and the Chocolate Factory"
    HARRY_POTTER      = "Harry Potter and the Philosopher's Stone"


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


class LabelSet(Base):

    id = Column(Integer, primary_key=True, autoincrement=True)

    work_id = Column(Integer, ForeignKey('parent.id'))
    work = relationship('Work', back_populates='labelset')

    # Handle Multiple Hues via a secondary association table, 
    # discerned via an 'ordinal' (primary/secondary/tertiary)
    hues = relationship(
        'Hue',
        secondary=labelset_hue_association_table,
        back_populates='books',
        lazy="selectin"
    )

    reading_ability = Column(Enum(ReadingAbility), nullable=True)

    doe_code = Column(Enum(DoeCode), nullable=True)

    # likely to be more robust than tagged concepts of a range i.e. "3to6" and "5to7"
    min_age = Column(Integer(3), nullable=True)
    max_age = Column(Integer(3), nullable=True)

    # e.g. 1000L
    lexile = Column(String(length=5), nullable=True)

    # unsure at this stage if huey picks will classify editions or works 
    # (e.g. will huey pick depending on illustrator and cover? or just text)
    huey_pick = Column(Boolean(), default=False)

    labelled_by = Column(String(length=30), nullable=True)

    # Could possibly add a pg trigger to update a last_modified timestamp for each
    # row, which could be compared against last_checked to enable a more meaningful
    # query in "show me works with unchecked updates". But repeated modifications to 
    # the labelset probably aren't likely at this stage, so the boolean will do for now.
        # last_checked = Column(DateTime(), nullable=True)
    checked = Column(Boolean(), default=False)

    def __repr__(self):
        return f"<LabelSet id={self.id} - '{self.work.title (self.work.isbn)}'>"

