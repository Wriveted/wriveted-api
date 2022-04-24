from typing import Optional
from sqlalchemy import update, select, delete
from sqlalchemy.orm import Session
from structlog import get_logger
from app.crud import CRUDBase
from app.models.booklist import BookList
from app.models.booklist_work_association import BookListItem
from app.schemas.booklist import (
    BookListCreateIn,
    BookListUpdateIn,
    ItemUpdateType,
    BookListItemUpdateIn,
)

logger = get_logger()


class CRUDBookList(CRUDBase[BookList, BookListCreateIn, BookListUpdateIn]):
    def create(self, db: Session, *, obj_in: BookListCreateIn, commit=True) -> BookList:
        items = obj_in.items
        obj_in.items = []
        booklist_orm_object = super().create(db=db, obj_in=obj_in, commit=commit)

        for item in items:
            self._add_item_to_booklist(
                db=db,
                booklist_orm_object=booklist_orm_object,
                item_update=BookListItemUpdateIn(
                    action=ItemUpdateType.ADD, **item.dict()
                ),
            )

        logger.debug("Refreshed booklist count", count=booklist_orm_object.book_count)
        return booklist_orm_object

    def get_all_query_with_optional_filters(
        self,
        db: Session,
        list_type: Optional[str] = None,
    ):
        booklists_query = self.get_all_query(db=db)

        if list_type is not None:
            booklists_query = booklists_query.where(BookList.type == list_type)

        return booklists_query

    def update(
        self, db: Session, *, db_obj: BookList, obj_in: BookListUpdateIn
    ) -> BookList:
        item_changes = obj_in.items if obj_in.items is not None else []
        del obj_in.items
        # Update the book list object
        booklist_orm_object = super().update(db=db, db_obj=db_obj, obj_in=obj_in)

        # Now update the items one by one
        for change in item_changes:
            match change.action:
                case ItemUpdateType.ADD:
                    self._add_item_to_booklist(
                        db=db, booklist_orm_object=db_obj, item_update=change
                    )
                case ItemUpdateType.UPDATE:
                    self._update_item_in_booklist(
                        db=db, booklist_id=db_obj.id, item_update=change
                    )
                case ItemUpdateType.REMOVE:
                    self._remove_item_from_booklist(
                        db=db, booklist_orm_object=db_obj, item_to_remove=change
                    )

        db.commit()
        db.refresh(booklist_orm_object)
        return booklist_orm_object

    def _update_item_in_booklist(
        self, db: Session, *, booklist_id: int, item_update: BookListItemUpdateIn
    ):
        item_orm_object = db.scalar(
            select(BookListItem)
            .where(BookListItem.booklist_id == booklist_id)
            .where(BookListItem.work_id == item_update.work_id)
        )
        if item_orm_object is None:
            logger.warning("Skipping update of missing item in booklist")
            return

        # Deal with an item's position change
        if item_update.order_id is not None:
            old_position = item_orm_object.order_id
            new_position = item_update.order_id
            if new_position < old_position:
                # Change requested is to move an item up - towards 0 (the start of the list)
                # E.g new_position=2, old_position=12
                # We have to move every item down the list one from the new insertion point to the old point.
                # Move every item greater than the new position but less than the old position down the list
                # by one position.
                stmt = (
                    update(BookListItem)
                    .where(BookListItem.booklist_id == booklist_id)
                    .where(BookListItem.order_id >= new_position)
                    .where(BookListItem.order_id < old_position)
                    .values(order_id=BookListItem.order_id + 1)
                )
            else:
                # Moving an item down towards the end of the list.
                # E.g new_position=10, old_position=2
                # Move every item above old position but less than new position up the list by one
                # We have to move every item that is after the insertion point
                stmt = (
                    update(BookListItem)
                    .where(BookListItem.booklist_id == booklist_id)
                    .where(BookListItem.order_id > old_position)
                    .where(BookListItem.order_id <= new_position)
                    .values(order_id=BookListItem.order_id - 1)
                )
            db.execute(stmt)
            item_orm_object.order_id = item_update.order_id
            if item_update.info is not None:
                item_orm_object.info = item_update.info
            db.add(item_orm_object)
            db.commit()
            db.refresh(item_orm_object)

    def _remove_item_from_booklist(
        self,
        db: Session,
        *,
        booklist_orm_object: BookList,
        item_to_remove: BookListItemUpdateIn
    ):
        item_position = db.scalar(
            select(BookListItem.order_id)
            .where(BookListItem.booklist_id == booklist_orm_object.id)
            .where(BookListItem.work_id == item_to_remove.work_id)
        )
        if item_position is None:
            logger.warning("Got asked to remove an item that is already removed")
            return

        db.execute(
            delete(BookListItem)
            .where(BookListItem.booklist_id == booklist_orm_object.id)
            .where(BookListItem.work_id == item_to_remove.work_id)
        )
        # Need to split this into two transactions to avoid violating the unique constraint
        db.commit()
        logger.debug(
            "Move all the following items up the list one", position=item_position
        )
        stmt = (
            update(BookListItem)
            .where(BookListItem.booklist_id == booklist_orm_object.id)
            .where(BookListItem.order_id > item_position)
            .values(order_id=BookListItem.order_id - 1)
        )
        db.execute(stmt)
        db.commit()
        db.refresh(booklist_orm_object)

    def _add_item_to_booklist(
        self,
        db: Session,
        *,
        booklist_orm_object: BookList,
        item_update: BookListItemUpdateIn
    ):
        # The slightly tricky bit here is to deal with the order_id
        if item_update.order_id is None:
            # Insert at the end of the booklist
            new_order_id = booklist_orm_object.book_count
        else:
            # We have to move every item that is after the insertion point
            stmt = (
                update(BookListItem)
                .where(BookListItem.booklist_id == booklist_orm_object.id)
                .where(BookListItem.order_id >= item_update.order_id)
                .values(order_id=BookListItem.order_id + 1)
            )
            db.execute(stmt)
            new_order_id = item_update.order_id

        new_orm_item = BookListItem(
            booklist_id=booklist_orm_object.id,
            work_id=item_update.work_id,
            info=item_update.info,
            order_id=new_order_id,
        )

        db.add(new_orm_item)
        db.commit()
        db.refresh(booklist_orm_object)
        return new_orm_item


booklist = CRUDBookList(BookList)
