from typing import Optional

from sqlalchemy.orm import Session
from structlog import get_logger

from app import crud
from app.models import Event, School
from app.models.booklist import ListType
from app.models.user import User, UserAccountType
from app.schemas.booklist import (
    BookListCreateIn,
    BookListItemInfo,
    BookListItemUpdateIn,
    BookListUpdateIn,
    ItemUpdateType,
)

logger = get_logger()


def process_events(session: Session, event: Event):
    logger.warning("Background processing event", type=event.title, event_id=event.id)
    match event.title:
        case "Huey: Book reviewed":
            return process_book_review_event(session, event)
        case _:
            return


def process_book_review_event(session: Session, event: Event):
    """
    Add liked books to booklists for optional school, class and user.

    Creates the booklists if they don't exist.
    """
    logger.info("Processing book review event")

    logger.debug("First we prepare a list of the liked books")
    liked_items = get_liked_books_from_book_review_event(session, event)

    if len(liked_items) == 0:
        logger.info("No liked books")
        return

    logger.info(f"Review included {len(liked_items)} liked books")

    # Work out if this review event is associated with a school
    if event.school is None:
        logger.debug("No school associated with book review")
    else:
        booklist = update_or_create_liked_books(
            session,
            liked_items,
            booklist_type=ListType.SCHOOL,
            school=event.school,
            user=event.user,
        )
        logger.info("Updated school booklist", booklist=booklist)

    if event.user is None:
        logger.debug("No user associated with book review")
    else:
        logger.debug("Updating personal list of liked books", user=event.user)
        personal_booklist = update_or_create_liked_books(
            session,
            liked_items,
            booklist_type=ListType.PERSONAL,
            school=None,
            user=event.user,
        )
        logger.info("Updated personal liked books", booklist=personal_booklist)

        if event.user.type == UserAccountType.STUDENT:
            class_group = event.user.class_group
            logger.debug("Updating class list of liked books", class_group=class_group)
            class_booklist = update_or_create_liked_books(
                session,
                liked_items,
                booklist_type=ListType.SCHOOL,
                school=event.school,
                user=event.user,
                booklist_name=f"{class_group.name} Liked Books",
            )
            logger.info("Updated class liked books", booklist=class_booklist)


def update_or_create_liked_books(
    session: Session,
    liked_items: list,
    booklist_type: str,
    school: Optional[School],
    user: Optional[User],
    booklist_name="Liked Books",
):
    # See if the "Liked Books" booklist exists.
    liked_booklist_query = crud.booklist.get_all_query_with_optional_filters(
        db=session,
        list_type=booklist_type,
        school=school,
        user=user,
        query_string=booklist_name,
    )
    booklist = session.scalars(liked_booklist_query).first()
    if booklist is None:
        logger.info("Creating a new booklist")
        booklist = crud.booklist.create(
            db=session,
            obj_in=BookListCreateIn(
                name=booklist_name,
                type=booklist_type,
                user_id=user.id if user is not None else None,
                school_id=school.id if school is not None else None,
                info={"description": "List of all books liked in a Chat"},
                items=liked_items,
            ),
        )
    else:
        logger.info("Updating existing booklist", booklist_id=booklist.id)
        booklist = crud.booklist.update(
            db=session, db_obj=booklist, obj_in=BookListUpdateIn(items=liked_items)
        )
    return booklist


def get_liked_books_from_book_review_event(session: Session, event: Event):
    liked_items = []
    logger.info("Getting liked books from event", event_info=event.info)

    if "reviews" not in event.info:
        logger.error("Unexpected event - couldn't find reviews")
        return []

    for review in event.info["reviews"]:
        logger.debug("Processing review", raw_review=review)
        edition = crud.edition.get(db=session, id=review["isbn"])
        if edition and review["liked"]:
            liked_items.append(
                BookListItemUpdateIn(
                    action=ItemUpdateType.ADD,
                    work_id=edition.work_id,
                    info=BookListItemInfo(
                        edition=review["isbn"],
                    ),
                )
            )
    return liked_items
