from typing import Any, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import asc, delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_upsert
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import Session, aliased
from structlog import get_logger

from app import crud
from app.crud import CRUDBase
from app.crud.base import deep_merge_dicts
from app.models import Edition
from app.models.collection import Collection
from app.models.collection_item import CollectionItem
from app.models.collection_item_activity import (
    CollectionItemActivity,
    CollectionItemReadStatus,
)
from app.schemas import is_url
from app.schemas.collection import (
    CollectionAndItemsUpdateIn,
    CollectionCreateIn,
    CollectionItemCreateIn,
    CollectionItemUpdate,
    CollectionUpdateType,
)
from app.services.cover_images import (
    handle_collection_item_cover_image_update,
    handle_new_collection_item_cover_image,
)
from app.services.editions import get_definitive_isbn

logger = get_logger()


class CRUDCollection(CRUDBase[Collection, Any, Any]):
    def create(
        self,
        db: Session,
        *,
        obj_in: CollectionCreateIn,
        commit=True,
        ignore_conflicts=False,
    ) -> Collection:
        items = obj_in.items or []
        obj_in.items = []
        collection_orm_object = super().create(db=db, obj_in=obj_in, commit=commit)
        logger.debug(
            "Collection entry created in database",
            collection_id=str(collection_orm_object.id),
        )

        logger.debug(
            f"Adding {len(items)} collection items to collection",
            collection_id=str(collection_orm_object.id),
        )
        for item in items:
            self.add_item_to_collection(
                db=db,
                collection_orm_object=collection_orm_object,
                item=item,
                commit=commit,
                ignore_conflicts=ignore_conflicts,
            )

        if commit:
            db.commit()

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
            logger.info(
                "Creating new collection",
                user_id=str(collection_data.user_id)
                if collection_data.user_id
                else None,
                school_id=str(collection_data.school_id)
                if collection_data.school_id
                else None,
                name=collection_data.name,
                num_items=len(collection_data.items or []),
            )
            collection = self.create(db, obj_in=collection_data, commit=commit)
            return collection, True

    def update(
        self,
        db: Session,
        *,
        db_obj: Collection,
        obj_in: CollectionAndItemsUpdateIn,
        merge_dicts: bool = True,
        commit: bool = True,
        ignore_conflicts: bool = False,
    ) -> Collection:
        if item_changes := getattr(obj_in, "items", []):
            del obj_in.items
        if item_changes is None:
            item_changes = []

        # Update the collection object
        collection_orm_object = super().update(
            db=db, db_obj=db_obj, obj_in=obj_in, merge_dicts=merge_dicts
        )

        # If provided, update the items one by one
        for change in item_changes:
            match change.action:
                case CollectionUpdateType.ADD:
                    try:
                        self.add_item_to_collection(
                            db=db,
                            collection_orm_object=collection_orm_object,
                            item=change,
                            commit=False,
                            ignore_conflicts=ignore_conflicts,
                        )
                    except IntegrityError as e:
                        raise e
                case CollectionUpdateType.UPDATE:
                    self._update_item_in_collection(
                        db=db,
                        collection_id=collection_orm_object.id,
                        item_update=change,
                        commit=False,
                    )
                case CollectionUpdateType.REMOVE:
                    self._remove_item_from_collection(
                        db=db,
                        collection_orm_object=collection_orm_object,
                        item_to_remove=change,
                        commit=False,
                    )

        if commit:
            db.commit()
            db.refresh(collection_orm_object)

        return collection_orm_object

    def delete_all_items(
        self,
        db: Session,
        *,
        db_obj: Collection,
        commit: bool = True,
    ) -> Collection:
        db.execute(
            delete(CollectionItem).where(CollectionItem.collection_id == db_obj.id)
        )

        if commit:
            db.commit()
            db.refresh(db_obj)

        return db_obj

    def _update_item_in_collection(
        self,
        db: Session,
        *,
        collection_id: int,
        item_update: CollectionItemUpdate | CollectionItemCreateIn,
        commit: bool = True,
    ):
        base_query = select(CollectionItem).where(
            CollectionItem.collection_id == collection_id
        )
        if item_update.id is not None:
            select_query = base_query.where(CollectionItem.id == item_update.id)
        else:
            select_query = base_query.where(
                CollectionItem.edition_isbn == item_update.edition_isbn
            )
        item_orm_object = db.scalar(select_query)
        if item_orm_object is None:
            logger.warning("Skipping update of missing item in collection")
            return

        if item_update.info is not None:
            info_dict = dict(item_orm_object.info)
            info_update_dict = item_update.info.dict(exclude_unset=True)

            if image_data := info_update_dict.get("cover_image"):
                logger.debug(
                    "Updating cover image for collection item",
                    collection_item_id=item_orm_object.id,
                )
                if is_url(image_data):
                    info_update_dict["cover_image"] = image_data
                else:
                    info_update_dict[
                        "cover_image"
                    ] = handle_collection_item_cover_image_update(
                        item_orm_object,
                        image_data,
                    )

            deep_merge_dicts(info_dict, info_update_dict)
            item_orm_object.info = info_dict

        if item_update.copies_available:
            item_orm_object.copies_available = item_update.copies_available

        if item_update.copies_total:
            item_orm_object.copies_total = item_update.copies_total

        if commit:
            logger.debug(
                "Committing item update", collection_item_id=item_orm_object.id
            )
            db.commit()
            db.refresh(item_orm_object)

        return item_orm_object

    def _remove_item_from_collection(
        self,
        db: Session,
        *,
        collection_orm_object: Collection,
        item_to_remove: CollectionItemUpdate | CollectionItemCreateIn,
        commit: bool = True,
    ):
        base_query = delete(CollectionItem).where(
            CollectionItem.collection_id == collection_orm_object.id
        )
        if item_to_remove.id is not None:
            # Prefer the case where the item id is provided instead of the isbn
            query = base_query.where(CollectionItem.id == item_to_remove.id)
        else:
            query = base_query.where(
                CollectionItem.edition_isbn == item_to_remove.edition_isbn
            )

        db.execute(query)

        if commit:
            db.commit()
            db.refresh(collection_orm_object)

    def add_items_to_collection(
        self,
        db: Session,
        *,
        collection_orm_object: Collection,
        items: list[CollectionItemUpdate | CollectionItemCreateIn],
        commit: bool = True,
    ):
        item_data = [
            {
                "collection_id": collection_orm_object.id,
                "edition_isbn": item.edition_isbn,
                "copies_available": item.copies_available or 1,
                "copies_total": item.copies_total or 1,
                "info": item.info or {},
            }
            for item in items
        ]

        stmt = pg_upsert(CollectionItem)
        stmt = stmt.on_conflict_do_update(
            constraint="unique_editions_per_collection",
            set_={
                "copies_available": stmt.excluded.copies_available,
            },
        )

        try:
            db.execute(stmt, item_data)
        except IntegrityError as e:
            logger.warning("Integrity Error while replacing collection")
            raise e

        if commit:
            db.commit()

    def add_item_to_collection(
        self,
        db: Session,
        *,
        collection_orm_object: Collection,
        item: CollectionItemUpdate | CollectionItemCreateIn,
        commit: bool = True,
        ignore_conflicts: bool = False,
    ):
        isbn = item.edition_isbn

        if isbn is not None:
            try:
                edition = crud.edition.get_or_create_unhydrated(
                    db=db, isbn=item.edition_isbn, commit=True
                )
                isbn = edition.isbn
            except AssertionError:
                # Invalid isbn, just skip
                logger.warning("Skipping invalid isbn", isbn=item.edition_isbn)
                return

        info_dict = {}
        if item.info is not None:
            info_dict = item.info.dict(exclude_unset=True)

            if cover_image_data := info_dict.get("cover_image"):
                logger.debug("Processing cover image for new collection item")
                if is_url(cover_image_data):
                    info_dict["cover_image"] = cover_image_data
                else:
                    info_dict["cover_image"] = handle_new_collection_item_cover_image(
                        str(collection_orm_object.id),
                        item.edition_isbn,
                        info_dict["cover_image"],
                    )

        new_orm_item_data = dict(
            collection_id=str(collection_orm_object.id),
            edition_isbn=isbn,
            copies_available=item.copies_available or 1,
            copies_total=item.copies_total or 1,
            info=info_dict,
        )

        # Supposed to be adding new items, but if the item exists
        # we just update it.
        stmt = (
            pg_upsert(CollectionItem).on_conflict_do_update(
                constraint="unique_editions_per_collection",
                set_=new_orm_item_data,
            )
            if ignore_conflicts
            else pg_upsert(CollectionItem)
        )

        try:
            result = db.execute(
                stmt.returning(CollectionItem.id),
                [new_orm_item_data],
            )
            new_id = result.scalar()

        except IntegrityError as e:
            raise IntegrityError(
                statement=f"Isbn {isbn} already exists in collection",
                params={},
                orig=e,
            ) from None

        if not isbn and collection_orm_object.school is not None:
            logger.warning(
                f"Item with no isbn added to a school collection #{collection_orm_object.id}"
            )
            crud.event.create(
                session=db,
                level="warning",
                title="Unknown Book added to Collection",
                description=f"Book with no isbn added to collection #{collection_orm_object.id}",
                info={
                    "collection_id": str(collection_orm_object.id),
                    "title": item.info.title if item.info else None,
                    "author": item.info.author if item.info else None,
                    "item_id": str(new_id),
                },
                school=collection_orm_object.school,
                account=collection_orm_object.user,
                commit=False,
            )

        if commit:
            db.commit()

        # return db.get(CollectionItem, new_id)
        return new_id

    def get_collection_items_by_collection_id(
        self, db: Session, *, collection_id: UUID
    ):
        return (
            db.execute(
                select(CollectionItem).where(
                    CollectionItem.collection_id == collection_id
                )
            )
            .scalars()
            .all()
        )

    def get_collection_item_by_collection_id_and_isbn(
        self, db: Session, *, collection_id: UUID, isbn: str
    ):
        return db.execute(
            select(CollectionItem)
            .where(CollectionItem.collection_id == collection_id.id)
            .where(CollectionItem.edition_isbn == get_definitive_isbn(isbn))
        ).scalar_one_or_none()

    def get_collection_item(
        self, db: Session, *, collection_item_id: int
    ) -> CollectionItem:
        return db.execute(
            select(CollectionItem).where(CollectionItem.id == collection_item_id)
        ).scalar_one_or_none()

    def get_collection_item_or_404(
        self, db: Session, *, collection_item_id: int
    ) -> CollectionItem:
        try:
            return db.execute(
                select(CollectionItem).where(CollectionItem.id == collection_item_id)
            ).scalar_one()
        except NoResultFound:
            raise HTTPException(
                status_code=404,
                detail=f"Collection Item with id {collection_item_id} not found.",
            )

    def get_filtered_with_count(
        self,
        db: Session,
        collection_id: UUID,
        query_string: Optional[str] = None,
        reader_id: Optional[UUID] = None,
        read_status: Optional[CollectionItemReadStatus] = None,
        skip: int = 0,
        limit: int = 1000,
    ):
        statement = (
            select(CollectionItem)
            .join(
                CollectionItem.edition, isouter=True
            )  # Note would be a joined load anyway, but now we can filter with it
            .where(CollectionItem.collection_id == collection_id)
            .order_by(asc(Edition.title))
        )

        if query_string is not None:
            statement = statement.where(Edition.title.match(query_string))

        if reader_id is not None or read_status is not None:
            statement = statement.join(CollectionItemActivity)

            if reader_id is not None:
                # filters for items that have been interacted with by a specific reader
                statement = statement.where(
                    CollectionItemActivity.reader_id == reader_id
                )

            if read_status is not None:
                # We need to join on the most recent activity for each item
                # (as this is effectively the "active" status)
                most_recent_timestamps = (
                    select(
                        CollectionItemActivity.collection_item_id,
                        CollectionItemActivity.reader_id,
                        func.max(CollectionItemActivity.timestamp).label(
                            "most_recent_timestamp"
                        ),
                    )
                    .group_by(
                        CollectionItemActivity.collection_item_id,
                        CollectionItemActivity.reader_id,
                    )
                    .alias("most_recent_timestamps")
                )

                statement = (
                    statement.where(
                        CollectionItem.id == CollectionItemActivity.collection_item_id
                    )
                    .where(
                        most_recent_timestamps.c.most_recent_timestamp
                        == CollectionItemActivity.timestamp
                    )
                    .where(
                        CollectionItemActivity.reader_id
                        == most_recent_timestamps.c.reader_id
                    )
                    .where(CollectionItemActivity.status == read_status)
                )

        # Note we can't use self.count_query here because the self.model is a Collection not a CollectionItem

        cte = statement.cte()
        aliased_model = aliased(CollectionItem, cte)
        matching_count = db.scalar(select(func.count(aliased_model.id)))

        paginated_items_query = self.apply_pagination(statement, skip=skip, limit=limit)

        return matching_count, db.scalars(paginated_items_query).all()


collection = CRUDCollection(Collection)
