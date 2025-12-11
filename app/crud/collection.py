"""
DEPRECATED: Use app.repositories.collection_repository instead.

This module is maintained for backward compatibility only.
"""

import warnings
from typing import Any, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session
from structlog import get_logger

from app.crud import CRUDBase
from app.models.collection import Collection
from app.models.collection_item import CollectionItem
from app.models.collection_item_activity import CollectionItemReadStatus
from app.repositories.collection_repository import collection_repository
from app.schemas.collection import (
    CollectionAndItemsUpdateIn,
    CollectionCreateIn,
    CollectionItemCreateIn,
    CollectionItemUpdate,
)

logger = get_logger()


class CRUDCollection(CRUDBase[Collection, Any, Any]):
    """DEPRECATED: Use CollectionRepository from app.repositories instead."""

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "CRUDCollection is deprecated. Use CollectionRepository from app.repositories.collection_repository",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)

    def create(
        self,
        db: Session,
        *,
        obj_in: CollectionCreateIn,
        commit=True,
        ignore_conflicts=False,
    ) -> Collection:
        """DEPRECATED: Delegates to collection_repository.create()."""
        return collection_repository.create(
            db=db, obj_in=obj_in, commit=commit, ignore_conflicts=ignore_conflicts
        )

    def get_or_create(
        self, db: Session, collection_data: CollectionCreateIn, commit=True
    ) -> Tuple[Collection, bool]:
        """DEPRECATED: Delegates to collection_repository.get_or_create()."""
        return collection_repository.get_or_create(
            db=db, collection_data=collection_data, commit=commit
        )

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
        """DEPRECATED: Delegates to collection_repository.update()."""
        return collection_repository.update(
            db=db,
            db_obj=db_obj,
            obj_in=obj_in,
            merge_dicts=merge_dicts,
            commit=commit,
            ignore_conflicts=ignore_conflicts,
        )

    def delete_all_items(
        self,
        db: Session,
        *,
        db_obj: Collection,
        commit: bool = True,
    ) -> Collection:
        """DEPRECATED: Delegates to collection_repository.delete_all_items()."""
        return collection_repository.delete_all_items(
            db=db, db_obj=db_obj, commit=commit
        )

    def _update_item_in_collection(
        self,
        db: Session,
        *,
        collection_id: UUID,
        item_update: CollectionItemUpdate | CollectionItemCreateIn,
        commit: bool = True,
    ):
        """DEPRECATED: Delegates to collection_repository._update_item_in_collection()."""
        return collection_repository._update_item_in_collection(
            db=db, collection_id=collection_id, item_update=item_update, commit=commit
        )

    def _remove_item_from_collection(
        self,
        db: Session,
        *,
        collection_orm_object: Collection,
        item_to_remove: CollectionItemUpdate | CollectionItemCreateIn,
        commit: bool = True,
    ):
        """DEPRECATED: Delegates to collection_repository._remove_item_from_collection()."""
        return collection_repository._remove_item_from_collection(
            db=db,
            collection_orm_object=collection_orm_object,
            item_to_remove=item_to_remove,
            commit=commit,
        )

    def add_items_to_collection(
        self,
        db: Session,
        *,
        collection_orm_object: Collection,
        items: list[CollectionItemUpdate | CollectionItemCreateIn],
        commit: bool = True,
    ):
        """DEPRECATED: Delegates to collection_repository.add_items_to_collection()."""
        return collection_repository.add_items_to_collection(
            db=db,
            collection_orm_object=collection_orm_object,
            items=items,
            commit=commit,
        )

    def add_item_to_collection(
        self,
        db: Session,
        *,
        collection_orm_object: Collection,
        item: CollectionItemUpdate | CollectionItemCreateIn,
        commit: bool = True,
        ignore_conflicts: bool = False,
    ):
        """DEPRECATED: Delegates to collection_repository.add_item_to_collection()."""
        return collection_repository.add_item_to_collection(
            db=db,
            collection_orm_object=collection_orm_object,
            item=item,
            commit=commit,
            ignore_conflicts=ignore_conflicts,
        )

    def get_collection_items_by_collection_id(
        self, db: Session, *, collection_id: UUID
    ):
        """DEPRECATED: Delegates to collection_repository.get_collection_items_by_collection_id()."""
        return collection_repository.get_collection_items_by_collection_id(
            db=db, collection_id=collection_id
        )

    def get_collection_item_by_collection_id_and_isbn(
        self, db: Session, *, collection_id: UUID, isbn: str
    ):
        """DEPRECATED: Delegates to collection_repository.get_collection_item_by_collection_id_and_isbn()."""
        return collection_repository.get_collection_item_by_collection_id_and_isbn(
            db=db, collection_id=collection_id, isbn=isbn
        )

    def get_collection_item(
        self, db: Session, *, collection_item_id: int
    ) -> CollectionItem:
        """DEPRECATED: Delegates to collection_repository.get_collection_item()."""
        return collection_repository.get_collection_item(
            db=db, collection_item_id=collection_item_id
        )

    def get_collection_item_or_404(
        self, db: Session, *, collection_item_id: int
    ) -> CollectionItem:
        """DEPRECATED: Delegates to collection_repository.get_collection_item_or_404()."""
        return collection_repository.get_collection_item_or_404(
            db=db, collection_item_id=collection_item_id
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
        """DEPRECATED: Delegates to collection_repository.get_filtered_with_count()."""
        return collection_repository.get_filtered_with_count(
            db=db,
            collection_id=collection_id,
            query_string=query_string,
            reader_id=reader_id,
            read_status=read_status,
            skip=skip,
            limit=limit,
        )


collection = CRUDCollection(Collection)
