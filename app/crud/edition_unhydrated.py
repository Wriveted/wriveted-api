from typing import Any, List
from sqlalchemy import func
from sqlalchemy.orm import Session
from structlog import get_logger
from app.crud import CRUDBase
from app.models.edition import Edition

from app.services.editions import clean_isbns
from sqlalchemy.dialects.postgresql import insert

# from db import insert_ignore

logger = get_logger()

class CRUDEditionUnhydrated(CRUDBase[Edition, Any, Any]):
    
    # To speed up the inserts, we've opted out orm features to track each object and retrieve each pk after insertion.
    # but since we know already have the isbns, i.e the pk's that are being inserted, we can refer to them later anyway.
    # After ensuring the list is added to the db, this returns the list of cleaned pk's.
    async def create_in_bulk_unhydrated(self, session: Session, isbn_list: List[str]):
        clean_isbn_list = clean_isbns(isbn_list)
        editions = [{"isbn" : isbn} for isbn in clean_isbn_list]

        previous_count = get_count(session)

        stmt=insert(Edition.__table__).values(editions).on_conflict_do_nothing()
        session.execute(stmt)
        session.commit()

        new_count = get_count(session)
        # can't seem to track how many conflicts the commit generates, so our best way
        # of tracking the amount that were actually created is to just generate a count diff
        num_created = new_count - previous_count

        logger.info(f"{num_created} unhydrated editions created")
        return clean_isbn_list, num_created


# faster way to count rows in a query
# avoids the query.count() "subquery" which can be slow with many rows
def get_count(session: Session):
    return session.execute(
        session.query(Edition.id)
        .statement.with_only_columns([func.count()]).order_by(None)
    ).scalar()


edition_unhydrated = CRUDEditionUnhydrated(Edition)