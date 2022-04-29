from typing import List

from fastapi import APIRouter, Depends, Security, BackgroundTasks
from sqlalchemy import delete, func, update, select
from sqlalchemy.orm import Session
from structlog import get_logger

from app.api.common.pagination import PaginatedQueryParams
from app.api.dependencies.school import get_school_from_wriveted_id
from app.api.dependencies.security import get_current_active_user_or_service_account
from app.api.dependencies.booklist import get_booklist_from_wriveted_id
from app.db.session import get_session
from app.models import BookList, CollectionItem, School, Edition
from app.permissions import Permission
from app.schemas.booklist_collection_intersection import (
    BookListItemInCollection,
    CollectionBookListIntersection,
)
from app.schemas.collection import (
    CollectionInfo,
    CollectionItemBase,
    CollectionItemDetail,
    CollectionUpdate,
    CollectionUpdateSummaryResponse,
    CollectionUpdateType,
    CollectionItemIn,
)
from app.schemas.pagination import Pagination

from app.services.collections import (
    add_editions_to_collection_by_isbn,
    get_collection_info_with_criteria,
    get_collection_items_also_in_booklist,
    reset_school_collection,
)
from app.services.events import create_event

logger = get_logger()

router = APIRouter(
    tags=["Library Collection"],
    dependencies=[
        # Shouldn't be necessary
        Security(get_current_active_user_or_service_account)
    ],
)


@router.get(
    "/school/{wriveted_identifier}/collection",
    response_model=List[CollectionItemDetail],
)
async def get_school_collection(
    school: School = Permission("read", get_school_from_wriveted_id),
    pagination: PaginatedQueryParams = Depends(),
    session: Session = Depends(get_session),
):
    logger.debug("Getting collection", pagination=pagination)
    collection_items = session.scalars(
        school.collection.statement.offset(pagination.skip).limit(pagination.limit)
    ).all()
    logger.debug("Loading collection", collection_size=len(collection_items))
    return collection_items


@router.get(
    "/school/{wriveted_identifier}/collection/info",
    response_model=CollectionInfo,
)
async def get_school_collection_info(
    school: School = Permission("read", get_school_from_wriveted_id),
    session: Session = Depends(get_session),
):
    """
    Endpoint returning information about how much of the collection is labeled.
    """
    logger.debug("Getting collection info")
    output = {}

    editions_query = select(func.count(CollectionItem.id)).where(
        CollectionItem.school_id == school.id
    )
    hydrated_query = get_collection_info_with_criteria(
        session, school.id, is_hydrated=True
    )
    labelled_query = get_collection_info_with_criteria(
        session, school.id, is_hydrated=True, is_labelled=True
    )
    recommend_query = get_collection_info_with_criteria(
        session, school.id, is_hydrated=True, is_labelled=True, is_recommendable=True
    )

    # explain_results = session.execute(explain(recommend_query, analyze=True)).scalars().all()
    # logger.info("Query plan")
    # for entry in explain_results:
    #     logger.info(entry)

    output["total_editions"] = session.execute(editions_query).scalar_one()
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


@router.get(
    "/school/{wriveted_identifier}/collection/compare-with-booklist/{booklist_identifier}",
    response_model=CollectionBookListIntersection,
)
async def get_school_collection_booklist_intersection(
    background_tasks: BackgroundTasks,
    school: School = Permission("read", get_school_from_wriveted_id),
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
        "Computing booklist collection intersection", school=school, booklist=booklist
    )

    paginated_booklist_item_query = booklist.items.statement.offset(
        pagination.skip
    ).limit(pagination.limit)

    common_collection_items = await get_collection_items_also_in_booklist(
        session,
        school,
        paginated_booklist_item_query,
    )
    common_work_ids = {item.work_id for item in common_collection_items}

    background_tasks.add_task(
        create_event,
        session,
        title="Compared booklist and collection",
        properties={
            "items_in_common": len(common_collection_items),
            "school_wriveted_id": str(school.wriveted_identifier),
            "booklist_id": str(booklist.id),
        },
        school=school,
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


@router.post(
    "/school/{wriveted_identifier}/collection",
    response_model=CollectionUpdateSummaryResponse,
)
async def set_school_collection(
    collection_data: List[CollectionItemIn],
    school: School = Permission("update", get_school_from_wriveted_id),
    account=Depends(get_current_active_user_or_service_account),
    session: Session = Depends(get_session),
):
    """
    Set the contents of a school library collection.

    Requires only an ISBN to identify each Edition, other attributes are optional. Note all editions will be stored as
    part of the collection, but as additional data is fetched from partner APIs it can take up to a few days before
    the editions are fully "hydrated".
    """
    logger.info(
        "Resetting the entire collection for school", school=school, account=account
    )
    reset_school_collection(session, school)

    logger.info(
        f"Adding/syncing {len(collection_data)} ISBNs with school collection",
        school=school,
        account=account,
    )
    if len(collection_data) > 0:
        await add_editions_to_collection_by_isbn(
            session, collection_data, school, account
        )

    count = session.execute(
        select(func.count(CollectionItem.id)).where(CollectionItem.school == school)
    ).scalar_one()

    return {
        "msg": f"Collection set. Total editions: {count}",
        "collection_size": count,
    }


@router.patch(
    "/school/{wriveted_identifier}/collection",
    response_model=CollectionUpdateSummaryResponse,
)
async def update_school_collection(
    collection_update_data: List[CollectionUpdate],
    school: School = Permission("update", get_school_from_wriveted_id),
    account=Depends(get_current_active_user_or_service_account),
    session: Session = Depends(get_session),
):
    """
    Update a school library collection with a list of changes.

    Changes can be to add, remove, or update editions of books. Many
    changes of different types can be added in a single call to this
    API, they must however all refer to one school.

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
    logger.info("Updating collection for school", school=school, account=account)

    isbns_to_remove: List[str] = []
    items_to_add: List[CollectionItemBase] = []

    for update_info in collection_update_data:
        if update_info.action == CollectionUpdateType.REMOVE:
            isbns_to_remove.append(update_info.isbn)
        elif update_info.action == CollectionUpdateType.ADD:
            items_to_add.append(update_info)
        elif update_info.action == CollectionUpdateType.UPDATE:
            # Update the "copies_total and "copies_available"
            # TODO consider a bulk update version of this
            stmt = (
                update(CollectionItem)
                .where(CollectionItem.school_id == school.id)
                .where(
                    # Note execution_options(synchronize_session="fetch") must be set
                    # for this subquery where clause to work.
                    # Ref https://docs.sqlalchemy.org/en/14/orm/session_basics.html#update-and-delete-with-arbitrary-where-clause
                    CollectionItem.edition.has(Edition.isbn == update_info.isbn)
                )
                .values(
                    copies_total=update_info.copies_total,
                    copies_available=update_info.copies_available,
                )
                .execution_options(synchronize_session="fetch")
            )

            session.execute(stmt)

    if len(isbns_to_remove) > 0:
        logger.info(f"Removing {len(isbns_to_remove)} items from collection")
        stmt = (
            delete(CollectionItem)
            .where(CollectionItem.school_id == school.id)
            .where(
                CollectionItem.edition_isbn.in_(
                    select(Edition.isbn).where(Edition.isbn.in_(isbns_to_remove))
                )
            )
            .execution_options(synchronize_session="fetch")
        )
        logger.info("Delete stmt", stmts=str(stmt))
        session.execute(stmt)

    if len(items_to_add) > 0:
        logger.info(f"Adding {len(items_to_add)} editions to collection")
        await add_editions_to_collection_by_isbn(session, items_to_add, school, account)

    logger.debug(f"Committing transaction")
    session.commit()
    count = session.execute(
        select(func.count(CollectionItem.id)).where(CollectionItem.school == school)
    ).scalar_one()

    return {"msg": "updated", "collection_size": count}
