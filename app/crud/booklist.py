from typing import Any

from sqlalchemy.orm import Session
from structlog import get_logger

from app.crud import CRUDBase
from app.models.booklist import BookList
from app.models.booklist_work_association import BookListItem
from app.schemas.booklist import BookListCreateIn, BookListUpdateIn, ItemUpdateType

logger = get_logger()


class CRUDBookList(CRUDBase[BookList, BookListCreateIn, BookListUpdateIn]):
    def create(self, db: Session, *, obj_in: BookListCreateIn, commit=True) -> BookList:
        items = obj_in.items
        obj_in.items = []
        booklist_orm_object = super().create(db=db, obj_in=obj_in, commit=commit)
        orm_items = [BookListItem(**item.dict()) for item in items]
        logger.debug("Preparing booklist items", item_count=len(orm_items))
        booklist_orm_object.items = orm_items
        db.add(booklist_orm_object)
        db.commit()
        db.refresh(booklist_orm_object)
        logger.debug("Refreshed booklist count", count=booklist_orm_object.book_count)
        return booklist_orm_object

    def update(
        self, db: Session, *, db_obj: BookList, obj_in: BookListUpdateIn
    ) -> BookList:
        item_changes = obj_in.items if obj_in.items is not None else []
        del obj_in.items
        # Update the book list object
        booklist_orm_object = super().update(db=db, db_obj=db_obj, obj_in=obj_in)

        # Now update the items
        for change in item_changes:
            match change.action:
                case ItemUpdateType.ADD:

                    booklist_orm_object.items.append(
                        BookListItem(work_id=change.work_id, info=change.info)
                    )
                case ItemUpdateType.UPDATE:
                    raise NotImplemented("Need to implement book list item update")
                case ItemUpdateType.REMOVE:
                    raise NotImplemented("Need to implement book list item removal")

        db.commit()
        db.refresh(booklist_orm_object)
        return booklist_orm_object


booklist = CRUDBookList(BookList)
