import enum

from sqlalchemy import (
    Enum,
    JSON,
    ForeignKey,
    Column,
    Integer,
    Boolean,
    DateTime,
    Text,
    func,
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.mutable import MutableDict
from app.db import Base
from app.models.labelset_reading_ability_association import labelset_reading_ability_association_table
from app.models.labelset_genre_association import labelset_genre_association_table
from datetime import datetime

class RecommendStatus(str, enum.Enum):
    GOOD = "GOOD" # Good to Recommend
    BAD_BORING = "BAD_BORING" # Too boring
    BAD_REFERENCE = "BAD_REFERENCE" # Reference/Education book
    BAD_CONTROVERSIAL = "BAD_CONTROVERSIAL" # Contoversial content
    BAD_LOW_QUALITY = "BAD_LOW_QUALITY" # Not a great example

# class ReadingAbility(str, enum.Enum):
    # SPOT = "SPOT" # Where's Spot
    # CAT_HAT = "CAT_HAT" # Cat in the Hat
    # TREEHOUSE = "TREEHOUSE" # The 13-Storey Treehouse
    # CHARLIE_CHOCOLATE = "CHARLIE_CHOCOLATE" # Charlie and the Chocolate Factory
    # HARRY_POTTER = "HARRY_POTTER" # Harry Potter and the Philosopher's Stone

class LabelOrigin(str, enum.Enum):
    HUMAN = "HUMAN" # Human-provided
    PREDICTED_NIELSEN = "PREDICTED_NIELSEN" # Predicted based on metadata from Nielsen
    CLUSTER_RELEVANCE = "CLUSTER_RELEVANCE" # Relevance AI cluster
    CLUSTER_ZAINAB = "CLUSTER_ZAINAB" # Original K-Means clustering by Zainab

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
    hue_relationships = relationship("LabelSetHue", back_populates="labelset")    
    hue_origin = Column(Enum(LabelOrigin), nullable=True)

    genres = relationship(
        "Genre",
        secondary=labelset_genre_association_table,
        back_populates="labelsets",
        lazy="selectin",
    )

    huey_summary = Column(Text, nullable=True)
    summary_origin = Column(Enum(LabelOrigin), nullable=True)

    reading_abilities = relationship(
        "ReadingAbility",
        secondary=labelset_reading_ability_association_table,
        back_populates="labelsets",
        lazy="selectin",
    )
    reading_ability_origin = Column(Enum(LabelOrigin), nullable=True)

    min_age = Column(Integer, nullable=True)
    max_age = Column(Integer, nullable=True)
    age_origin = Column(Enum(LabelOrigin), nullable=True)

    recommend_status = Column(Enum(RecommendStatus), nullable=False, server_default="GOOD")
    recommend_status_origin = Column(Enum(LabelOrigin), nullable=True)

    # both service accounts and users could potentially label works
    labelled_by_user_id = Column(
        ForeignKey("users.id", name="fk_labeller-user_labelset"), nullable=True
    )
    labelled_by_sa_id = Column(
        ForeignKey("service_accounts.id", name="fk_labeller-sa_labelset"), nullable=True
    )

    info = Column(MutableDict.as_mutable(JSON))

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    checked = Column(Boolean(), nullable=False, default=False)

    def __repr__(self):
        return f"<LabelSet id={self.id} - '{self.work.title}'>"
