import datetime
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased
from starlette import status
from structlog import get_logger

from app import crud

from app.models import CollectionItem
from app.models.edition import Edition
from app.models.hue import Hue
from app.models.labelset import LabelSet, RecommendStatus
from app.models.labelset_hue_association import LabelSetHue
from app.models.labelset_reading_ability_association import LabelSetReadingAbility
from app.models.reading_ability import ReadingAbility
from app.models.school import School
from app.models.work import Work
from app.schemas.collection import CollectionItemBase, CollectionItemIn
from app.services.events import create_event
from app.services.editions import (
    create_missing_editions,
    create_missing_editions_unhydrated,
    get_definitive_isbn,
)

logger = get_logger()


async def add_editions_to_collection(
    session, new_edition_data: List[CollectionItemIn], school, account
):
    logger.info("Adding editions to collection", account=account, school=school)

    (
        all_referenced_edition_isbns,
        created_edition_isbns,
        existing_edition_isbns,
    ) = await create_missing_editions(session, new_edition_data)

    # At this point all editions referenced should exist
    logger.info(f"Adding {len(all_referenced_edition_isbns)} editions to collection")
    if len(created_edition_isbns) > 0:
        logger.info(f"{len(created_edition_isbns)} editions haven't been seen before")

    edition_orms_by_isbn = {
        e.isbn: e
        for e in crud.edition.get_multi(
            session, ids=all_referenced_edition_isbns, limit=None
        )
    }
    # If the list of new editions include the same ISBN multiple times just process the first one
    processed_isbns = set()
    for collection_item_info in new_edition_data:
        isbn = get_definitive_isbn(collection_item_info.isbn)
        if isbn not in processed_isbns:
            school.collection.append(
                CollectionItem(
                    edition=edition_orms_by_isbn[isbn],
                    info={"Updated": str(datetime.datetime.utcnow())},
                    # TODO this is gross because I pass EditionCreateIn as well as CollectionCreateIn
                    copies_total=collection_item_info.copies_total
                    if hasattr(collection_item_info, "copies_total")
                    else 1,
                    copies_available=collection_item_info.copies_available
                    if hasattr(collection_item_info, "copies_available")
                    else 1,
                )
            )
            processed_isbns.add(isbn)
        else:
            logger.warning(
                "Duplicate ISBN present in api call. Ignoring subsequent entries",
                isbn=isbn,
            )
    create_event(
        session=session,
        title="Updating collection",
        description=f"Updating {len(existing_edition_isbns)} existing editions, adding {len(created_edition_isbns)} new editions",
        school=school,
        account=account,
        commit=False,
    )

    # session.add(school)

    try:
        session.commit()
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Couldn't process input",
        )


# Mostly the same as add_editions_to_collection, but only processes a list of isbns.
# Due to the lack of EditionCreateIns, any created editions will be unhydrated
async def add_editions_to_collection_by_isbn(
    session, collection_data: List[CollectionItemBase], school: School, account
):
    logger.info("Adding editions to collection by ISBN", account=account, school=school)
    collection_counts = {}
    for item in collection_data:
        try:
            isbn = get_definitive_isbn(item.isbn)
        except AssertionError:
            # Invalid isbn, just skip
            continue

        collection_counts[isbn] = {
            "copies_total": item.copies_total if item.copies_total is not None else 1,
            "copies_available": item.copies_available
            if item.copies_available is not None
            else 1,
        }

    isbn_list = list(collection_counts.keys())
    # Insert the entire list of isbns, ignoring conflicts, returning a list of the pk's for the CollectionItem binding
    (
        final_primary_keys,
        num_editions_created,
    ) = await crud.edition.create_in_bulk_unhydrated(session, isbn_list=isbn_list)

    if not final_primary_keys:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No valid ISBNs were found in input",
        )

    # At this point all editions referenced should exist.
    # Using len(final_primary_keys) as length may be different now that it's a set
    logger.info(f"Syncing {len(final_primary_keys)} editions with collection")

    collection_items = []
    for isbn in final_primary_keys:
        collection_items.append(
            {
                "school_id": school.id,
                "edition_isbn": isbn,
                "info": {"Updated": str(datetime.datetime.utcnow())},
                "copies_total": collection_counts[isbn]["copies_total"]
                if isbn in collection_counts
                else 1,
                "copies_available": collection_counts[isbn]["copies_available"]
                if isbn in collection_counts
                else 1,
            }
        )

    num_collection_items_created = await crud.collection_item.create_in_bulk(
        session, school.id, collection_items
    )

    create_event(
        session=session,
        title="Updating collection",
        description=f"Adding {num_collection_items_created - num_editions_created} existing editions, adding {num_editions_created} new, unhydrated editions",
        school=school,
        account=account,
        commit=False,
    )

    # session.add(school)

    try:
        session.commit()
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Couldn't process input",
        )


def get_collection_info_with_criteria(
    session,
    school_id: int,
    is_hydrated: bool = False,
    is_labelled: bool = False,
    is_recommendable: bool = False,
):
    """
    Return a (complicated) select query for labelsets, editions, and works filtering by
    school, hydration status, labelling status, and recommendability.

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
        # .join(LabelSetHue, LabelSetHue.labelset_id == aliased_labelset.id)
        # .join(LabelSetReadingAbility, LabelSetReadingAbility.labelset_id == aliased_labelset.id)
    )

    # Filter for works in a school collection
    school = crud.school.get_or_404(db=session, id=school_id)
    query = query.join(
        CollectionItem, CollectionItem.edition_isbn == Edition.isbn
    ).where(CollectionItem.school == school)

    if is_hydrated:
        query = query.where(Edition.title.is_not(None))
        query = query.where(Edition.cover_url.is_not(None))

    if is_labelled:
        query = (
            query.where(aliased_labelset.hues.any())
            .where(aliased_labelset.reading_abilities.any())
            .where(aliased_labelset.min_age >= 0)
            .where(aliased_labelset.max_age > 0)
            .where(aliased_labelset.huey_summary.is_not(None))
        )

    if is_recommendable:
        query = query.where(aliased_labelset.recommend_status == RecommendStatus.GOOD)

    return query
