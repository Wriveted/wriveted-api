from uuid import UUID
from sqlalchemy.orm import Session
from structlog import get_logger

from app.crud import CRUDBase
from app.models import Reader
from app.models.collection_item_activity import (
    CollectionItemActivity,
    CollectionItemReadStatus,
)
from app.schemas.collection import CollectionItemActivityBase

logger = get_logger()


class CRUDCollectionItemActivity(
    CRUDBase[
        CollectionItemActivity, CollectionItemActivityBase, CollectionItemActivityBase
    ]
):
    def get_all_query_with_optional_filters(
        self,
        db: Session,
        collection_item_id: UUID | None = None,
        reader: Reader | None = None,
        status: CollectionItemReadStatus | None = None,
    ):
        collection_item_activity_query = self.get_all_query(
            db=db, order_by=CollectionItemActivity.timestamp.desc()
        )

        if collection_item_id is not None:
            collection_item_activity_query = collection_item_activity_query.where(
                CollectionItemActivity.collection_item_id == collection_item_id
            )
        if reader is not None:
            collection_item_activity_query = collection_item_activity_query.where(
                CollectionItemActivity.reader == reader
            )
        if status is not None:
            collection_item_activity_query = collection_item_activity_query.where(
                CollectionItemActivity.status == status
            )

        return collection_item_activity_query


collection_item_activity = CRUDCollectionItemActivity(CollectionItemActivity)
