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
from sqlalchemy.ext.mutable import MutableDict
from app.db import Base
from app.models.labelset_hue_association import labelset_hue_association_table
from app.models.labelset_genre_association import labelset_genre_association_table

class RecommendStatus(str, enum.Enum):
    GOOD = "Good to Recommend"
    BAD_BORING = "Too boring"
    BAD_REFERENCE = "Reference/Education book"
    BAD_CONTROVERSIAL = "Contoversial content"
    BAD_LOW_QUALITY = "Not a great example"

class ReadingAbility(str, enum.Enum):
    SPOT = "Where's Spot"
    CAT_HAT = "Cat in the Hat"
    TREEHOUSE = "The 13-Storey Treehouse"
    CHARLIE_CHOCOLATE = "Charlie and the Chocolate Factory"
    HARRY_POTTER = "Harry Potter and the Philosopher's Stone"

# an abstraction of the "label" related properties of a Work, which are likely to be human-provided.
# this is what Huey will look at when making recommendations, and the fields can sometimes be computed
# by combining data from editions' metdata.
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

    min_age = Column(Integer, nullable=True)
    max_age = Column(Integer, nullable=True)

    recommend_status = Column(Enum(RecommendStatus), nullable=False, server_default="GOOD")

    # both service accounts and users could potentially label works
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
        return f"<LabelSet id={self.id} - '{self.work.title}'>"
