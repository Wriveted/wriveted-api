from sqlalchemy import distinct, func, select
from sqlalchemy.orm import aliased
from typing import Optional

from structlog import get_logger
from app.models import (
    CollectionItem,
    Edition,
    Hue,
    LabelSet,
    LabelSetHue,
    ReadingAbility,
    Work,
    LabelSetReadingAbility,
)

from app import crud
from app.models.labelset import RecommendStatus

logger = get_logger()


def get_recommended_labelset_query(
    session,
    hues: Optional[list[str]] = None,
    school_id: Optional[int] = None,
    age: Optional[int] = None,
    reading_abilities: Optional[list[str]] = None,
    recommendable_only: Optional[bool] = True,
    exclude_isbns: Optional[list[str]] = None,
):
    """
    Return a (complicated) select query for labelsets filtering by hue,
    and optional school, reading ability and age range.

    The returned query can be used directly to access recommended works:

    Can raise sqlalchemy.exc.NoResultFound if for example an invalid reading_ability key
    is passed.
    """
    latest_labelset_subquery = (
        select(LabelSet)
        .distinct(LabelSet.work_id)
        .order_by(LabelSet.work_id, LabelSet.id.desc())
        .cte(name="latestlabelset")
    )
    aliased_labelset = aliased(LabelSet, latest_labelset_subquery)
    query = (
        select(Work, Edition, aliased_labelset)
        .select_from(aliased_labelset)
        .distinct(Work.id)
        .order_by(Work.id)
        .join(Work, aliased_labelset.work_id == Work.id)
        .join(Edition, Edition.work_id == Work.id)
        .join(LabelSetHue, LabelSetHue.labelset_id == aliased_labelset.id)
        .join(
            LabelSetReadingAbility,
            LabelSetReadingAbility.labelset_id == aliased_labelset.id,
        )
    )

    # Now add the optional filters
    if school_id is not None:
        # Filter for works in a school collection
        school = crud.school.get_or_404(db=session, id=school_id)
        query = (
            query.join(
                CollectionItem, CollectionItem.edition_isbn == Edition.isbn
            ).where(CollectionItem.school == school)
            # Could order by other things, but consider indexes
            # .order_by(Work.id, CollectionItem.copies_available.desc())
        )

    if hues is not None:
        # Labelset Ids from hues
        hue_ids_query = select(Hue.id).where(Hue.key.in_(hues))
        query = query.where(LabelSetHue.hue_id.in_(hue_ids_query))

    if reading_abilities is not None:
        # Labelset Ids from reading abilities
        reading_ability_ids_query = select(ReadingAbility.id).where(
            ReadingAbility.key.in_(reading_abilities)
        )
        query = query.where(
            LabelSetReadingAbility.reading_ability_id.in_(reading_ability_ids_query)
        )

    if age is not None:
        query = query.where(aliased_labelset.min_age <= age).where(
            aliased_labelset.max_age >= age
        )

    # Add other filtering criteria
    if recommendable_only:
        query = query.where(aliased_labelset.recommend_status == RecommendStatus.GOOD)
    query = query.where(Edition.cover_url.is_not(None)).limit(100)
    # To exclude images from the OpenLibrary bucket folder
    # query = query.filter(~Edition.cover_url.contains("/open/"))

    # exclude certain editions using isbn
    if exclude_isbns is not None:
        query = query.where(~Edition.isbn.in_(exclude_isbns))

    # Now make a massive CTE so we can shuffle the results
    massive_cte = query.cte(name="labeled")

    aliased_work = aliased(Work, massive_cte)
    aliased_edition = aliased(Edition, massive_cte)
    aliased_labelset_end = aliased(LabelSet, massive_cte)

    return select(aliased_work, aliased_edition, aliased_labelset_end).order_by(
        func.random()
    )
