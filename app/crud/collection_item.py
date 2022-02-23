from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from structlog import get_logger

from app.crud import CRUDBase
from app.models import Illustrator
from app.models.collection_item import CollectionItem

logger = get_logger()

class CRUDCollectionItem(CRUDBase[CollectionItem, Any, Any]):
    
    # To speed up the inserts, we've opted out orm features to track each object and retrieve each pk after insertion.
    # but since we know already have the isbns, i.e the pk's that are being inserted, we can refer to them later anyway.
    # After ensuring the list is added to the db, this returns the list of cleaned pk's.
    async def create_in_bulk(self, session: Session, school_id, collection_items: list[CollectionItem]):

        previous_count = get_count(session, school_id)

        stmt=insert(CollectionItem.__table__).values(collection_items).on_conflict_do_nothing()
        session.execute(stmt)
        session.commit()

        new_count = get_count(session, school_id)
        # can't seem to track how many conflicts the commit generates, so our best way
        # of tracking the amount that were actually created is to just generate a count diff
        num_created = new_count - previous_count

        logger.info(f"{num_created} editions added to collection of school #{school_id}")
        return num_created


# faster way to count rows in a query
# avoids the query.count() "subquery" which can be slow with many rows
def get_count(session: Session, school_id):
    return session.execute(
        session.query(CollectionItem.id).filter(CollectionItem.school_id == school_id)
        .statement.with_only_columns([func.count()]).order_by(None)
    ).scalar()


collection_item = CRUDCollectionItem(Illustrator)
