import datetime
from typing import List

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from starlette import status
from structlog import get_logger

from app import crud

from app.models import Edition, CollectionItem
from app.schemas.collection import CollectionItemIn
from app.services.events import create_event
from app.services.editions import create_missing_editions, get_definitive_isbn

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
        e.ISBN: e
        for e in crud.edition.get_multi(
            session, ids=all_referenced_edition_isbns, limit=None
        )
    }
    # If the list of new editions include the same ISBN multiple times just process the first one
    processed_isbns = set()
    for collection_item_info in new_edition_data:
        isbn = get_definitive_isbn(collection_item_info.ISBN)
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
