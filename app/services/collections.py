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
    CollectionAndItemsUpdateIn,
    CollectionItemCreateIn,
    CollectionUpdateType,
)
from app.services.editions import get_definitive_isbn

logger = get_logger()


async def update_collection(
    session,
    collection: Collection,
    account,
    obj_in: CollectionAndItemsUpdateIn,
    merge_dicts: bool = True,
    ignore_conflicts: bool = False,
):
    item_changes = getattr(obj_in, "items", [])
    if item_changes is None:
        item_changes = []

    if len(item_changes) > 0:
        logger.info(
            f"Applying {len(item_changes)} changes",
            collection_id=str(collection.id),
            collection_name=collection.name,
        )
    summary_counts = {"added": 0, "removed": 0, "updated": 0}
    # If provided, update the items one by one
    # First process in bulk editions added or updated by ISBN

    added_items = []
    updated_items = []
    for change in item_changes:
        if change.action == CollectionUpdateType.ADD and hasattr(change, "isbn"):
            added_items.append(change)
        elif change.action == CollectionUpdateType.UPDATE and hasattr(change, "isbn"):
            updated_items.append(change)

    if len(added_items) > 0:
        await add_editions_to_collection_by_isbn(
            session, added_items, collection, account
        )
        session.flush()
        logger.debug("Added editions", collection_id=str(collection.id))

    if len(updated_items) > 0:
        # Note this will create new editions - may need to change.
        await add_editions_to_collection_by_isbn(
            session, updated_items, collection, account
        )
        session.flush()
        logger.debug("Updated editions", collection_id=str(collection.id))

    obj_in.items = [
        item
        for item in item_changes
        if CollectionUpdateType.REMOVE or not hasattr(item, "isbn")
    ]
    logger.info(f"Update items now has {len(obj_in.items)} items")

    logger.debug(
        "Updating the collection object itself", collection_id=str(collection.id)
    )
    collection = crud.collection.update(
        db=session,
        db_obj=collection,
        obj_in=obj_in,
        merge_dicts=merge_dicts,
        ignore_conflicts=ignore_conflicts,
        commit=False,
    )
    logger.debug(
        "Committing update to collection",
        collection_id=str(collection.id),
        collection_name=collection.name,
    )
    session.commit()
    logger.debug(
        "Committed update to collection",
        collection_id=str(collection.id),
        collection_name=collection.name,
    )

    return collection


async def add_editions_to_collection_by_isbn(
    session,
    collection_data: List[CollectionItemCreateIn],
    collection: Collection,
    account,
):
    """
    Mostly the same as add_editions_to_collection, but only processes a list of isbns.
    Due to the lack of EditionCreateIns, any created editions will be unhydrated
    """
    logger.info(
        "Adding editions to collection by ISBN", account=account, collection=collection
    )

    items = {}
    for item in collection_data:
        try:
            item.edition_isbn = get_definitive_isbn(item.edition_isbn)
        except AssertionError:
            # Invalid isbn, just skip
            continue

        item.copies_total = item.copies_total or 1
        item.copies_available = item.copies_available or item.copies_total

        items[item.edition_isbn] = item

    isbn_list = list(items.keys())

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

    crud.collection.add_items_to_collection(
        session,
        collection_orm_object=collection,
        items=[items[isbn] for isbn in final_primary_keys],
        commit=False,
    )

    num_collection_items_created = len(final_primary_keys)

    crud.event.create(
        session=session,
        title="Collection Update",
        description=f"Adding {num_collection_items_created} editions to collection",
        info={
            "collection_items_created_count": num_collection_items_created,
            "unhydrated_edition_count": num_editions_created,
            "collection_id": str(collection.id),
        },
        account=account,
        commit=False,
    )
    logger.debug("Committing changes to collection")

    try:
        session.commit()
        logger.debug("Changes committed to collection")
    except IntegrityError:
        logger.warning(
            "IntegrityError when adding editions to collection", exc_info=True
        )
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
    crud.collection.delete_all_items(db=session, db_obj=collection, commit=False)

    crud.event.create(
        session=session,
        title="Collection Reset",
        description=f"Reset collection #{str(collection.id)}, deleting all items",
        info={"collection_id": str(collection.id)},
        account=account,
        commit=True,
    )
