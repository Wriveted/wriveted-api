from sqlalchemy import select
from sqlalchemy.orm import aliased
from typing import Optional

from structlog import get_logger
from app.models import CollectionItem, Edition, Hue, LabelSet, LabelSetHue, ReadingAbility, Work

from app import crud


logger = get_logger()


def get_recommended_labelset_query(
        session,
        hues: list[str],
        school_id: Optional[int] = None,
        age: Optional[int] = None,
        reading_ability: Optional[str] = None
):
    """
    Return a (complicated) select query for labelsets filtering by hue,
    and optional school, reading ability and age range.

    The returned query can be used directly to access recommended works:

    >>> for labelset in session.execute(labelset_query.limit(5)).scalars().all():
    >>>     print(labelset.work)

    Can raise sqlalchemy.exc.NoResultFound if for example an invalid reading_ability key
    is passed.
    """
    if school_id is not None:
        # Let's filter works in a school collection
        school = crud.school.get_or_404(db=session, id=school_id)

        base_works_query = (
            select(Work)
                .join(CollectionItem, CollectionItem.work_id == Work.id)
                .where(CollectionItem.school == school)
        )
    else:
        base_works_query = (crud.work.get_all_query(db=session))

    # Labelset Ids from hues
    hue_ids_query = (
        select(Hue.id)
            .where(Hue.key.in_(hues))
    )
    labelset_id_query = (
        select(LabelSetHue.labelset_id)
            .where(LabelSetHue.hue_id.in_(hue_ids_query))
            .order_by(LabelSetHue.ordinal.asc())
    )

    work_subquery = aliased(Work, base_works_query.subquery())
    work_ids_query = select(Work.id).select_from(work_subquery)

    labelset_query = (
        select(LabelSet)
            .join(Work, Work.id == LabelSet.work_id)
            .where(LabelSet.id.in_(labelset_id_query))
            .where(LabelSet.work_id.in_(work_ids_query))

    )

    if reading_ability is not None:
        reading_ability_query = (
            select(ReadingAbility)
                .where(ReadingAbility.key == reading_ability)
                .limit(1)
        )
        reading_ability_id = session.execute(reading_ability_query).scalar_one().id

        labelset_query = (
            labelset_query
                .where(LabelSet.reading_abilities.any(ReadingAbility.id == reading_ability_id))
        )

    if age is not None:
        labelset_query = (
            labelset_query
                .where(LabelSet.min_age < age)
                .where(LabelSet.max_age > age)
        )

    return labelset_query


def get_school_specific_edition_and_labelset_query(school_id, labelset_query):
    # Now "just" include the correct edition...
    labelset_subq = aliased(LabelSet, labelset_query.subquery())
    work_id_query = (
        select(Work.id)
            .join_from(Work, labelset_subq)
    )

    return (
        select(Edition, LabelSet)
            .select_from(CollectionItem)
            .where(CollectionItem.school_id == school_id)
            .where(CollectionItem.edition_isbn == Edition.isbn)
            .where(CollectionItem.work_id.in_(work_id_query))
            .where(LabelSet.work_id == Edition.work_id)
    )


