from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session
from structlog import get_logger

from app import crud
from app.models import BookList, ServiceAccount, User
from app.models.booklist import ListSharingType, ListType
from app.repositories.booklist_repository import booklist_repository
from app.schemas.booklist import BookListCreateIn, BookListUpdateIn
from app.services.booklists import populate_booklist_object, validate_booklist_publicity

logger = get_logger()


class BookListService:
    """Service layer for booklist operations (sync Session)."""

    def create(
        self,
        session: Session,
        *,
        data: BookListCreateIn,
        account: User | ServiceAccount,
    ) -> BookList:
        validate_booklist_publicity(data)
        bl = booklist_repository.create(db=session, obj_in=data, commit=True)
        crud.event.create(
            session=session,
            title="Booklist created",
            description=f"{account.name} created booklist '{data.name}'",
            info={"type": data.type, "id": str(bl.id)},
            account=account,
        )
        return bl

    def list(
        self,
        session: Session,
        *,
        list_type: Optional[ListType] = None,
        sharing_type: Optional[ListSharingType] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[BookList], int]:
        q = booklist_repository.get_all_query_with_optional_filters(
            db=session, list_type=list_type, sharing_type=sharing_type
        )
        items = session.scalars(
            booklist_repository.apply_pagination(query=q, skip=skip, limit=limit)
        ).all()
        total = booklist_repository.count_query(db=session, query=q)
        return items, total

    def update(
        self, session: Session, *, obj: BookList, changes: BookListUpdateIn
    ) -> BookList:
        validate_booklist_publicity(changes, obj)
        return booklist_repository.update(db=session, db_obj=obj, obj_in=changes)

    def delete(self, session: Session, *, obj: BookList) -> None:
        booklist_repository.remove(db=session, id=obj.id)

    def get_detail(
        self,
        session: Session,
        *,
        obj: BookList,
        enriched: bool,
        skip: int,
        limit: int,
    ):
        return populate_booklist_object(
            obj, session, type("P", (), {"skip": skip, "limit": limit}), enriched
        )
