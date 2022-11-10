import datetime
from typing import List
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased
from starlette import status
from structlog import get_logger

from app import crud
from app.models import BookListItem, CollectionItem
from app.models.collection import Collection
from app.models.edition import Edition
from app.models.labelset import LabelSet, RecommendStatus
from app.models.work import Work
from app.schemas.collection import (
    CollectionAndItemsUpdate,
    CollectionItemBase,
    CollectionItemUpdate,
    CollectionUpdateIn,
    CollectionUpdateType,
)
from app.services.editions import get_definitive_isbn

logger = get_logger()


# Mostly the same as add_editions_to_collection, but only processes a list of isbns.
# Due to the lack of EditionCreateIns, any created editions will be unhydrated
async def add_editions_to_collection_by_isbn(
    session, collection_data: List[CollectionItemBase], collection: Collection, account
):
    logger.info(
        "Adding editions to collection by ISBN", account=account, collection=collection
    )
    collection_counts = {}
    for item in collection_data:
        try:
            isbn = get_definitive_isbn(item.edition_isbn)
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
        data = {
            "edition_isbn": isbn,
            "copies_total": collection_counts[isbn]["copies_total"]
            if isbn in collection_counts.keys()
            else 1,
            "copies_available": collection_counts[isbn]["copies_available"]
            if isbn in collection_counts.keys()
            else 1,
            "action": CollectionUpdateType.ADD,
        }
        collection_items.append(CollectionItemUpdate(**data))

    updated = crud.collection.update(
        db=session,
        db_obj=collection,
        obj_in=CollectionAndItemsUpdate(items=collection_items),
    )
    num_collection_items_created = len(updated.items)

    num_existing_editions = num_collection_items_created - num_editions_created
    crud.event.create(
        session=session,
        title="Collection Update",
        description=f"Adding {num_existing_editions} existing editions, adding {num_editions_created} new, unhydrated editions",
        info={
            "collection_items_created_count": num_collection_items_created,
            "existing_edition_count": num_existing_editions,
            "unhydrated_edition_count": num_editions_created,
            "collection_id": str(collection.id),
        },
        account=account,
        commit=False,
    )

    try:
        session.commit()
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Couldn't process input",
        )


def get_collection_info_with_criteria(
    collection_id: UUID,
    is_hydrated: bool = False,
    is_labelled: bool = False,
    is_recommendable: bool = False,
):
    """
    Return a (complicated) select query for labelsets, editions, and works filtering by
    collection, hydration status, labelling status, and recommendability.

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

    # Filter for works in a given collection
    query = query.join(
        CollectionItem, CollectionItem.edition_isbn == Edition.isbn
    ).where(CollectionItem.collection_id == collection_id)

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


async def get_collection_items_also_in_booklist(
    session, collection, paginated_booklist_item_query
) -> list[CollectionItem]:

    paginated_booklist_cte = paginated_booklist_item_query.cte(
        name="paginated_booklist_items"
    )

    aliased_booklist_item = aliased(BookListItem, paginated_booklist_cte)
    booklist_item_work_id_query = select(aliased_booklist_item.work_id)
    common_collection_items = session.scalars(
        collection.items.statement.where(
            CollectionItem.work_id.in_(booklist_item_work_id_query)
        )
    ).all()

    return common_collection_items


def reset_collection(session, collection: Collection, account):
    """
    Reset a collection to its initial state, removing all items
    """
    crud.collection.delete_all_items(db=session, db_obj=collection)

    crud.event.create(
        session=session,
        title="Collection Reset",
        description=f"Reset collection #{collection.id}, deleting all items",
        info={},
        account=account,
        commit=True,
    )
