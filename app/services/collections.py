import datetime

from sqlalchemy import select
from structlog import get_logger

from app import crud

from app.models import Edition, CollectionItem
from app.services.events import create_event

logger = get_logger()


async def add_editions_to_collection(session, new_edition_data, school, account):
    logger.info("Adding editions to collection", account=account, school=school)

    (
        all_referenced_edition_isbns,
        created_edition_isbns,
        existing_edition_isbns
     ) = await create_missing_editions(session, new_edition_data)

    # At this point all editions referenced should exist
    logger.info("Adding editions to collection")
    for edition in crud.edition.get_multi(session, ids=all_referenced_edition_isbns):
        school.collection.append(
            CollectionItem(
                edition=edition,
                info={
                    "Updated": str(datetime.datetime.utcnow())
                },
            )
        )
    create_event(
        session=session,
        title="Updating collection",
        description=f"Updating {len(existing_edition_isbns)} existing editions, adding {len(created_edition_isbns)} new editions",
        school=school,
        account=account
    )
    logger.info("Commiting collection")
    session.add(school)
    session.commit()


async def create_missing_editions(session, new_edition_data):
    isbns = {e.ISBN for e in new_edition_data if len(e.ISBN) > 0}
    existing_isbns = session.execute(select(Edition.ISBN).where(Edition.ISBN.in_(isbns))).scalars().all()
    isbns_to_create = isbns.difference(existing_isbns)
    logger.info(f"Will have to create {len(isbns_to_create)} new editions")
    new_edition_data = [data for data in new_edition_data if data.ISBN in isbns_to_create]
    crud.edition.create_in_bulk(session, bulk_edition_data=new_edition_data)
    logger.info("Created new editions")
    return isbns, isbns_to_create, existing_isbns
