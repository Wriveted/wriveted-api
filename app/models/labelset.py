import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Text,
    and_,
    func,
)
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import mapped_column, relationship, Mapped

from app.db import Base
from app.models.labelset_hue_association import LabelSetHue
from app.models.labelset_reading_ability_association import LabelSetReadingAbility


class RecommendStatus(str, enum.Enum):
    GOOD = "GOOD"  # Good to Recommend
    BAD_BORING = "BAD_BORING"  # Too boring
    BAD_REFERENCE = "BAD_REFERENCE"  # Reference/Education book
    BAD_CONTROVERSIAL = "BAD_CONTROVERSIAL"  # Controversial content
    BAD_LOW_QUALITY = "BAD_LOW_QUALITY"  # Not a great example


class LabelOrigin(str, enum.Enum):
    HUMAN = "HUMAN"  # Human-provided
    PREDICTED_NIELSEN = "PREDICTED_NIELSEN"  # Predicted based on metadata from Nielsen
    NIELSEN_CBMC = "NIELSEN_CBMC"
    NIELSEN_BIC = "NIELSEN_BIC"
    NIELSEN_THEMA = "NIELSEN_THEMA"
    NIELSEN_IA = "NIELSEN_IA"
    NIELSEN_RA = "NIELSEN_RA"
    CLUSTER_RELEVANCE = "CLUSTER_RELEVANCE"  # Relevance AI cluster
    CLUSTER_ZAINAB = "CLUSTER_ZAINAB"  # Original K-Means clustering by Zainab
    OTHER = "OTHER"


# an abstraction of the "label" related properties of a Work, which are likely to be human-provided.
# this is what Huey will look at when making recommendations, and the fields can sometimes be computed
# by combining data from editions' metdata.
class LabelSet(Base):

    id = mapped_column(Integer, primary_key=True, autoincrement=True)

    work_id = mapped_column(
        ForeignKey("works.id", name="fk_labelset_work"), nullable=True, index=True
    )
    work = relationship("Work", back_populates="labelset")

    # Create an index used to find the most recent labelsets for a work
    Index(
        "index_work_labelsets",
        work_id,
        id.desc(),
    )

    # Handle Multiple Hues via a secondary association table,
    # discerned via an 'ordinal' (primary/secondary/tertiary)
    hues = relationship(
        "Hue",
        secondary=LabelSetHue.__table__,
        lazy="selectin",
    )

    hue_origin = mapped_column(Enum(LabelOrigin), nullable=True)

    huey_summary = mapped_column(Text, nullable=True)
    summary_origin = mapped_column(Enum(LabelOrigin), nullable=True)

    reading_abilities = relationship(
        "ReadingAbility",
        secondary=LabelSetReadingAbility.__table__,
        back_populates="labelsets",
        lazy="selectin",
    )
    reading_ability_origin = mapped_column(Enum(LabelOrigin), nullable=True)

    min_age = mapped_column(Integer, nullable=True)
    max_age = mapped_column(Integer, nullable=True)
    Index(
        "index_age_range",
        min_age,
        max_age,
        postgresql_where=and_(min_age.is_not(None), max_age.is_not(None)),
    )

    age_origin = mapped_column(Enum(LabelOrigin), nullable=True)

    recommend_status = mapped_column(
        Enum(RecommendStatus), nullable=False, server_default="GOOD"
    )
    Index(
        "index_good_recommendations",
        recommend_status,
        postgresql_where=(recommend_status == RecommendStatus.GOOD),
    )

    recommend_status_origin = mapped_column(Enum(LabelOrigin), nullable=True)

    # both service accounts and users could potentially label works
    labelled_by_user_id = mapped_column(
        ForeignKey("users.id", name="fk_labeller-user_labelset"), nullable=True
    )
    labelled_by_sa_id = mapped_column(
        ForeignKey("service_accounts.id", name="fk_labeller-sa_labelset"), nullable=True
    )

    info: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON))

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    checked: Mapped[bool] = mapped_column(Boolean(), nullable=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    def __repr__(self):
        return f"<LabelSet id={self.id} - '{self.work.title}' ages: {self.min_age}-{self.max_age} >"

    def __str__(self):
        hues = [h.name for h in self.hues]
        reading_abilities = [ra.key for ra in self.reading_abilities]
        return f"'{self.work.title}' reading ability: {reading_abilities} ages: {self.min_age}-{self.max_age} Hues: {hues}"
