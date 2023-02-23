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
from app.schemas.collection import CollectionItemCreateIn
from app.services.editions import get_definitive_isbn

logger = get_logger()


# Mostly the same as add_editions_to_collection, but only processes a list of isbns.
# Due to the lack of EditionCreateIns, any created editions will be unhydrated
async def add_editions_to_collection_by_isbn(
    session,
    collection_data: List[CollectionItemCreateIn],
    collection: Collection,
    account,
):
    existing_collection_count = collection.book_count

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
    crud.collection.delete_all_items(db=session, db_obj=collection, commit=False)

    crud.event.create(
        session=session,
        title="Collection Reset",
        description=f"Reset collection #{str(collection.id)}, deleting all items",
        info={"collection_id": str(collection.id)},
        account=account,
        commit=True,
    )
