from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Security
from sqlalchemy import delete, func, select
from sqlalchemy import asc, delete, func, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from structlog import get_logger

from app import crud
from app.api.common.pagination import PaginatedQueryParams
from app.api.dependencies.booklist import get_booklist_from_wriveted_id
from app.api.dependencies.collection import (
    get_collection_from_id,
    validate_collection_creation,
)
from app.api.dependencies.editions import get_edition_from_isbn
from app.api.dependencies.security import get_current_active_user_or_service_account
from app.db.session import get_session
from app.models import BookList, CollectionItem, Edition
from app.models.collection import Collection
from app.permissions import Permission
from app.schemas.booklist_collection_intersection import (
    BookListItemInCollection,
    CollectionBookListIntersection,
)
from app.schemas.collection import (
    CollectionAndItemsUpdateIn,
    CollectionBrief,
    CollectionCreateIn,
    CollectionInfo,
    CollectionItemBase,
    CollectionItemDetail,
    CollectionUpdateSummaryResponse,
)
from app.schemas.pagination import Pagination
from app.services.collections import (
    add_editions_to_collection_by_isbn,
    get_collection_info_with_criteria,
    get_collection_items_also_in_booklist,
    reset_collection,
)

logger = get_logger()

router = APIRouter(
    tags=["Book Collection"],
    dependencies=[
        # Shouldn't be necessary
        Security(get_current_active_user_or_service_account)
    ],
)


@router.get(
    "/collection/{collection_id}",
    response_model=CollectionBrief,
)
async def get_collection_details(
    collection: Collection = Permission("read", get_collection_from_id),
):
    """
    Get a summary of an existing collection.
    """
    return collection


@router.get(
    "/collection/{collection_id}/items",
    response_model=List[CollectionItemDetail],
)
async def get_collection_items(
    collection: Collection = Permission("read", get_collection_from_id),
    pagination: PaginatedQueryParams = Depends(),
    session: Session = Depends(get_session),
):
    """
    Paginate the items in an existing collection.
    """
    logger.debug("Getting collection items", pagination=pagination)

    collection_items = session.scalars(
        select(CollectionItem)
        .join(
            CollectionItem.edition, isouter=True
        )  # Note would be a joined load anyway, but now we can filter with it
        .where(CollectionItem.collection_id == collection.id)
        .order_by(asc(Edition.title))
        .offset(pagination.skip)
        .limit(pagination.limit)
    ).all()

    logger.debug("Loading collection", collection_size=len(collection_items))
    return collection_items


@router.get(
    "/collection/{collection_id}/{isbn}",
    response_model=CollectionItemDetail,
)
async def get_collection_item(
    collection: Collection = Permission("read", get_collection_from_id),
    edition: Edition = Depends(get_edition_from_isbn),
    session: Session = Depends(get_session),
):
    """
    Returns a selected item from a collection, raising a 404 if it doesn't exist (either in the collection or at all).
    """
    logger.debug(
        f"Searching collection {collection.id} for edition {edition.isbn}",
    )

    collection_item = session.execute(
        select(CollectionItem)
        .where(CollectionItem.collection_id == collection.id)
        .where(CollectionItem.edition_isbn == edition.isbn)
    ).scalar_one_or_none()

    if collection_item is None:
        raise HTTPException(
            status_code=404,
            detail=f"Collection {collection.id} does not contain edition {edition.isbn}",
        )

    return collection_item


@router.get(
    "/collection/{id}/info",
    response_model=CollectionInfo,
)
async def get_collection_info(
    collection: Collection = Permission("read", get_collection_from_id),
    session: Session = Depends(get_session),
):
    """
    Endpoint returning information about how much of the collection is labeled.
    """
    logger.debug("Getting collection info")
    output = {}

    hydrated_query = get_collection_info_with_criteria(collection.id, is_hydrated=True)
    labelled_query = get_collection_info_with_criteria(
        collection.id, is_hydrated=True, is_labelled=True
    )
    recommend_query = get_collection_info_with_criteria(
        collection.id, is_hydrated=True, is_labelled=True, is_recommendable=True
    )

    # explain_results = session.execute(explain(recommend_query, analyze=True)).scalars().all()
    # logger.info("Query plan")
    # for entry in explain_results:
    #     logger.info(entry)

    output["total_editions"] = collection.book_count
    output["hydrated"] = session.execute(
        select(func.count()).select_from(hydrated_query)
    ).scalar_one()
    output["hydrated_and_labeled"] = session.execute(
        select(func.count()).select_from(labelled_query)
    ).scalar_one()
    output["recommendable"] = session.execute(
        select(func.count()).select_from(recommend_query)
    ).scalar_one()

    return output


@router.post(
    "/collection",
    response_model=CollectionBrief,
    dependencies=[Depends(validate_collection_creation)],
)
async def create_collection(
    collection_data: CollectionCreateIn,
    session: Session = Depends(get_session),
    ignore_conflicts: bool = Query(
        default=True,
        description="""Whether or not to ignore duplicate entries in the collection. Note: only one copy of an edition can be held in a collection - 
        this parameter simply controls whether or not an error is raised if a duplicate is found""",
    ),
):
    """
    Endpoint for creating a new collection, provided a collection isn't already assigned to the target user or school
    """
    logger.debug("Creating collection")
    try:
        return crud.collection.create(
            session, obj_in=collection_data, ignore_conflicts=ignore_conflicts
        )
    except IntegrityError as e:
        raise HTTPException(
            status_code=409,
            detail=e,
        )


@router.delete("/collection/{collection_id}")
async def delete_collection(
    collection: Collection = Permission("delete", get_collection_from_id),
    session: Session = Depends(get_session),
):
    """
    Endpoint to delete a collection.
    """
    logger.debug("Deleting collection")
    session.execute(delete(Collection).where(Collection.id == collection.id))
    session.commit()
    return {"message": "Collection deleted"}


@router.put(
    "/collection/{collection_id}",
    response_model=CollectionBrief,
)
async def set_collection(
    collection_data: CollectionCreateIn,
    collection: Collection = Permission("delete", get_collection_from_id),
    session: Session = Depends(get_session),
    ignore_conflicts: bool = Query(
        default=True,
        description="""Whether or not to ignore duplicate entries in the collection. Note: only one copy of an edition can be held in a collection - 
        this parameter simply controls whether or not an error is raised if a duplicate is found""",
    ),
):
    """
    Endpoint for replacing an existing collection and its items.
    """
    logger.debug("Deleting collection")
    session.execute(delete(Collection).where(Collection.id == collection.id))
    logger.debug("Replacing deleted collection")
    try:
        return crud.collection.create(
            session, obj_in=collection_data, ignore_conflicts=ignore_conflicts
        )
    except IntegrityError as e:
        raise HTTPException(
            status_code=409,
            detail=e,
        )


@router.get(
    "/collection/{collection_id}/compare-with-booklist/{booklist_identifier}",
    response_model=CollectionBookListIntersection,
)
async def get_collection_booklist_intersection(
    background_tasks: BackgroundTasks,
    collection: Collection = Permission("read", get_collection_from_id),
    booklist: BookList = Permission("read", get_booklist_from_wriveted_id),
    pagination: PaginatedQueryParams = Depends(),
    session: Session = Depends(get_session),
    account=Depends(get_current_active_user_or_service_account),
):
    """
    Endpoint returning information about which items in a booklist are part of a collection.

    Pagination applies to the booklist
    """
    logger.debug(
        "Computing booklist collection intersection",
        collection=collection,
        booklist=booklist,
    )

    paginated_booklist_item_query = booklist.items.statement.offset(
        pagination.skip
    ).limit(pagination.limit)

    common_collection_items = await get_collection_items_also_in_booklist(
        session,
        collection,
        paginated_booklist_item_query,
    )
    common_work_ids = {item.work_id for item in common_collection_items}

    background_tasks.add_task(
        crud.event.create,
        session,
        title="Compared booklist and collection",
        info={
            "items_in_common": len(common_collection_items),
            "collection_id": str(collection.id),
            "booklist_id": str(booklist.id),
        },
        collection=collection,
        account=account,
    )

    return CollectionBookListIntersection(
        pagination=Pagination(**pagination.to_dict(), total=booklist.book_count),
        data=[
            BookListItemInCollection(
                in_collection=booklist_item.work_id in common_work_ids,
                work_id=booklist_item.work_id,
                work_brief=booklist_item.work,
                editions_in_collection=[
                    collection_item.edition_isbn
                    for collection_item in common_collection_items
                    if collection_item.work_id == booklist_item.work_id
                ],
            )
            for booklist_item in session.scalars(paginated_booklist_item_query)
        ],
    )


@router.put(
    "/collection/{collection_id}/items",
    response_model=CollectionUpdateSummaryResponse,
)
async def set_collection_items(
    collection_data: List[CollectionItemBase],
    collection: Collection = Permission("update", get_collection_from_id),
    account=Depends(get_current_active_user_or_service_account),
    session: Session = Depends(get_session),
):
    """
    Set the contents of a collection.

    Requires only an ISBN to identify each Edition, other attributes are optional. Note all editions will be stored as
    part of the collection, but as additional data is fetched from partner APIs it can take up to a few days before
    the editions are fully "hydrated".
    """
    logger.info(
        "Resetting an entire collection",
        collection=collection,
        account=account,
    )
    reset_collection(session, collection, account)

    logger.info(
        f"Adding/syncing {len(collection_data)} ISBNs with collection",
        collection=collection,
        account=account,
    )
    if len(collection_data) > 0:
        await add_editions_to_collection_by_isbn(
            session, collection_data, collection, account
        )

    count = session.execute(
        select(func.count(CollectionItem.id)).where(
            CollectionItem.collection == collection
        )
    ).scalar_one()

    return {
        "msg": f"Collection set. Total editions: {count}",
        "collection_size": count,
    }


@router.patch(
    "/collection/{collection_id}",
    response_model=CollectionUpdateSummaryResponse,
)
async def update_collection(
    collection_update_data: CollectionAndItemsUpdateIn,
    collection: Collection = Permission("update", get_collection_from_id),
    account=Depends(get_current_active_user_or_service_account),
    session: Session = Depends(get_session),
    merge_dicts: bool = Query(
        default=False,
        description="Whether or not to *merge* the data in info dict, i.e. if adding new or updating existing individual fields (but want to keep previous data)",
    ),
    ignore_conflicts: bool = Query(
        default=True,
        description="""Whether or not to ignore duplicate entries in the collection. Note: only one copy of an edition can be held in a collection - 
        this parameter simply controls whether or not an error is raised if a duplicate is found""",
    ),
):
    """
    Update a collection itself, and/or its items with a list of changes.

    Changes can be to add, remove, or update editions of books. Many
    changes of different types can be added in a single call to this
    API, they must however all refer to one collection.

    If the edition are already in the Wriveted database only the ISBN
    and `"action"` is required. For example adding known editions to a
    collection can be achieved with entries of this form:

    ```json
    { "isbn": "XYZ", "action": "add" }
    ```

    Note: any unknown editions will be created as unhydrated, empty objects in the db.
    To provide metadata for new books, please use the `POST /editions` endpoint.

    ### Action Types

    - `add`
    - `remove`
    - `update` - change the `copies_total` and `copies_available`

    """
    logger.info("Updating collection", collection=collection, account=account)

    try:
        crud.collection.update(
            db=session,
            db_obj=collection,
            obj_in=collection_update_data,
            merge_dicts=merge_dicts,
            ignore_conflicts=ignore_conflicts,
        )
    except IntegrityError as e:
        raise HTTPException(
            status_code=409,
            detail=e.statement,
        )

    logger.debug("Committing transaction")
    session.commit()
    count = session.execute(
        select(func.count(CollectionItem.id)).where(
            CollectionItem.collection_id == collection.id
        )
    ).scalar_one()

    return {"msg": "updated", "collection_size": count}
