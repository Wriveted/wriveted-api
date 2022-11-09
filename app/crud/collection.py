from typing import Any, Tuple

from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound
from structlog import get_logger

from app.crud import CRUDBase
from app.crud.base import deep_merge_dicts
from app.models.collection import Collection
from app.models.collection_item import CollectionItem
from app.schemas.collection import (
    CollectionAndItemsUpdate,
    CollectionCreateIn,
    CollectionItemBase,
    CollectionItemUpdate,
    CollectionUpdateIn,
    CollectionUpdateType,
)

logger = get_logger()


class CRUDCollection(CRUDBase[Collection, Any, Any]):
    def create(
        self, db: Session, *, obj_in: CollectionCreateIn, commit=True
    ) -> Collection:
        items = obj_in.items or []
        obj_in.items = []
        collection_orm_object = super().create(db=db, obj_in=obj_in, commit=commit)
        logger.debug(
            "Collection entry created in database",
            collection_id=collection_orm_object.id,
        )

        logger.debug(
            f"Adding {len(items)} collection items to collection",
            collection_id=collection_orm_object.id,
        )
        for item in items:
            self._add_item_to_collection(
                db=db, collection_orm_object=collection_orm_object, item=item
            )

        return collection_orm_object

    def get_or_create(
        self, db: Session, collection_data: CollectionCreateIn, commit=True
    ) -> Tuple[Collection, bool]:
        """
        Get a collection by school or user id, creating a new collection if required.
        """
        if collection_data.user_id:
            q = select(Collection).where(Collection.user_id == collection_data.user_id)
        else:
            q = select(Collection).where(
                Collection.school_id == collection_data.school_id
            )
        try:
            collection = db.execute(q).scalar_one()
            return collection, False
        except NoResultFound:
            logger.info("Creating new collection", data=collection_data)
            collection = self.create(db, obj_in=collection_data, commit=commit)
            return collection, True

    def update(
        self,
        db: Session,
        *,
        db_obj: Collection,
        obj_in: CollectionAndItemsUpdate | CollectionItemUpdate,
    ) -> Collection:
        if item_changes := getattr(obj_in, "items", []):
            del obj_in.items

        # Update the collection object
        collection_orm_object = super().update(db=db, db_obj=db_obj, obj_in=obj_in)

        # If provided, update the items one by one
        for change in item_changes:
            match change.action:
                case CollectionUpdateType.ADD:
                    self._add_item_to_collection(
                        db=db, collection_orm_object=db_obj, item=change
                    )
                case CollectionUpdateType.UPDATE:
                    self._update_item_in_collection(
                        db=db, collection_id=db_obj.id, item_update=change
                    )
                case CollectionUpdateType.REMOVE:
                    self._remove_item_from_collection(
                        db=db, collection_orm_object=db_obj, item_to_remove=change
                    )

        db.commit()
        db.refresh(collection_orm_object)
        return collection_orm_object

    def delete_all_items(self, db: Session, *, db_obj: Collection) -> Collection:
        db.execute(
            delete(CollectionItem).where(CollectionItem.collection_id == db_obj.id)
        )
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def _update_item_in_collection(
        self,
        db: Session,
        *,
        collection_id: int,
        item_update: CollectionItemUpdate | CollectionItemBase,
    ):
        item_orm_object = db.scalar(
            select(CollectionItem)
            .where(CollectionItem.collection_id == collection_id)
            .where(CollectionItem.work_id == item_update.work_id)
        )
        if item_orm_object is None:
            logger.warning("Skipping update of missing item in collection")
            return

        if item_update.info is not None:
            info_dict = dict(item_orm_object.info)
            update_dict = dict(item_update.info)
            deep_merge_dicts(info_dict, update_dict)
            item_orm_object.info = info_dict

        if item_update.copies_available:
            item_orm_object.copies_available = item_update.copies_available

        if item_update.copies_total:
            item_orm_object.copies_total = item_update.copies_total

        db.add(item_orm_object)
        db.commit()
        db.refresh(item_orm_object)
        return item_orm_object

    def _remove_item_from_collection(
        self,
        db: Session,
        *,
        collection_orm_object: Collection,
        item_to_remove: CollectionItemUpdate | CollectionItemBase,
    ):
        db.execute(
            delete(CollectionItem)
            .where(CollectionItem.collection_id == collection_orm_object.id)
            .where(CollectionItem.edition_isbn == item_to_remove.edition_isbn)
        )
        db.commit()
        db.refresh(collection_orm_object)

    def _add_item_to_collection(
        self,
        db: Session,
        *,
        collection_orm_object: Collection,
        item: CollectionItemUpdate | CollectionItemBase,
    ):
        new_orm_item = CollectionItem(
            collection_id=collection_orm_object.id,
            edition_isbn=item.edition_isbn,
            copies_available=item.copies_available,
            copies_total=item.copies_total,
        )
        db.add(new_orm_item)
        db.commit()
        db.refresh(collection_orm_object)
        return new_orm_item


collection = CRUDCollection(Collection)
