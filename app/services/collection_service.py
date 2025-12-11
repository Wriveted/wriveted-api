from __future__ import annotations

from typing import List, Optional, Tuple

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session
from structlog import get_logger

from app import crud
from app.models.collection import Collection
from app.models.collection_item import CollectionItem
from app.models.collection_item_activity import CollectionItemReadStatus
from app.repositories.collection_item_activity_repository import (
    collection_item_activity_repository,
)
from app.schemas.collection import (
    CollectionAndItemsUpdateIn,
    CollectionCreateIn,
    CollectionItemActivityBase,
    CollectionItemAndStatusCreateIn,
    CollectionItemCreateIn,
)
from app.services.collections import (
    add_editions_to_collection_by_isbn,
    reset_collection,
)
from app.services.collections import update_collection as svc_update_collection

logger = get_logger()


class CollectionService:
    """
    Service layer for collection operations.

    Orchestrates CRUD helpers and SQL with clear transaction points.
    """

    # Reads
    def list_items(
        self,
        session: Session,
        *,
        collection_id,
        query: Optional[str],
        reader_id: Optional[str],
        read_status: Optional[CollectionItemReadStatus],
        skip: int,
        limit: int,
    ) -> Tuple[int, List[CollectionItem]]:
        return crud.collection.get_filtered_with_count(
            db=session,
            collection_id=collection_id,
            query_string=query,
            reader_id=reader_id,
            read_status=read_status,
            skip=skip,
            limit=limit,
        )

    # Writes
    def create_collection(
        self,
        session: Session,
        *,
        data: CollectionCreateIn,
        ignore_conflicts: bool,
    ) -> Collection:
        created = crud.collection.create(
            session, obj_in=data, commit=True, ignore_conflicts=ignore_conflicts
        )
        return created

    def replace_collection(
        self,
        session: Session,
        *,
        existing: Collection,
        data: CollectionCreateIn,
        ignore_conflicts: bool,
    ) -> Collection:
        session.execute(delete(Collection).where(Collection.id == existing.id))
        session.flush()
        return self.create_collection(
            session, data=data, ignore_conflicts=ignore_conflicts
        )

    def delete_collection(self, session: Session, *, collection: Collection) -> None:
        session.execute(delete(Collection).where(Collection.id == collection.id))
        session.commit()

    def add_collection_item(
        self,
        session: Session,
        *,
        collection: Collection,
        item: CollectionItemAndStatusCreateIn,
    ) -> CollectionItem:
        read_status = item.read_status
        reader_id = item.reader_id
        item_data = CollectionItemCreateIn(
            edition_isbn=item.edition_isbn,
            copies_total=item.copies_total,
            copies_available=item.copies_available,
            info=item.info,
        )
        item_id = crud.collection.add_item_to_collection(
            session, item=item_data, collection_orm_object=collection
        )
        obj = session.get(CollectionItem, item_id)

        if read_status or reader_id:
            collection_item_activity_repository.create(
                session,
                obj_in=CollectionItemActivityBase(
                    collection_item_id=obj.id,
                    status=read_status,
                    reader_id=str(reader_id) if reader_id else None,
                ),
            )
        session.commit()
        return obj

    async def set_collection_items(
        self,
        session,
        *,
        collection: Collection,
        items: List[CollectionItemCreateIn],
        account,
    ) -> dict:
        reset_collection(session, collection, account)
        if items:
            await add_editions_to_collection_by_isbn(
                session, items, collection, account
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

    async def update_collection(
        self,
        session,
        *,
        collection: Collection,
        account,
        changes: CollectionAndItemsUpdateIn,
        merge_dicts: bool,
        ignore_conflicts: bool,
    ) -> Collection:
        updated = await svc_update_collection(
            session=session,
            collection=collection,
            account=account,
            obj_in=changes,
            merge_dicts=merge_dicts,
            ignore_conflicts=ignore_conflicts,
        )
        return updated
