from uuid import UUID
from app import crud
from app.db.session import get_session_maker, SessionManager
from app.schemas.booklist import (
    BookListCreateIn,
    BookListItemCreateIn,
    BookListItemInfo,
)
from app.models.booklist import ListType
from app.schemas.users.huey_attributes import HueyAttributes
from app.services.recommendations import (
    gen_next_reading_ability,
    get_recommended_labelset_query,
)
from structlog import get_logger

logger = get_logger()


def generate_reading_pathway_lists(
    user_id: str, attributes: HueyAttributes, limit: int = 10, commit: bool = True
):
    """
    Generate booklists `Books to read now` and `Books to read next` for the provided user,
    populating each with `limit` appropriate books based on the provided `huey_attributes`
    """

    Session = get_session_maker()
    with Session() as session:
        try:
            current_reading_ability = attributes.reading_ability[0]
        except (ValueError, TypeError, IndexError):
            logger.warning(
                "Attempt to create reading pathway when no Huey attributes were provided",
                user_id=user_id,
            )
            return

        # Get the read now list by generating 10 books via standard recommendation
        current_reading_ability_key = current_reading_ability.name
        read_now_query = get_recommended_labelset_query(
            session,
            hues=attributes.hues,
            age=attributes.age,
            reading_abilities=[current_reading_ability_key],
        )

        # Get the read next list by incrementing the reading ability and doing the same
        next_reading_ability_key = gen_next_reading_ability(
            current_reading_ability
        ).name
        read_next_query = get_recommended_labelset_query(
            session,
            hues=attributes.hues,
            age=attributes.age,
            reading_abilities=[next_reading_ability_key],
        )

        now_results = session.execute(read_now_query.limit(limit)).all()
        items_to_read_now = [
            BookListItemCreateIn(
                work_id=work.id,
                info=BookListItemInfo(
                    edition=edition.isbn,
                ),
            )
            for (work, edition, _labelset) in now_results
        ]
        read_now_booklist_data = BookListCreateIn(
            name="Books To Read Now",
            type=ListType.PERSONAL,
            user_id=str(user_id),
            items=items_to_read_now,
            info={"description": "A collection of books to enjoy today"},
        )

        next_results = session.execute(read_next_query.limit(limit)).all()
        items_to_read_next = [
            BookListItemCreateIn(
                work_id=work.id,
                info=BookListItemInfo(
                    edition=edition.isbn,
                ),
            )
            for (work, edition, _labelset) in next_results
        ]
        read_next_booklist_data = BookListCreateIn(
            name="Books To Read Next",
            type=ListType.PERSONAL,
            user_id=str(user_id),
            items=items_to_read_next,
            info={
                "description": "A collection of books to enjoy tomorrow, or challenge your reading"
            },
        )

        read_now_orm = crud.booklist.create(
            session, obj_in=read_now_booklist_data, commit=commit
        )
        read_next_orm = crud.booklist.create(
            session, obj_in=read_next_booklist_data, commit=commit
        )

        crud.event.create(
            session,
            title="Created reading pathway lists",
            description="Created Books To Read Now and Books To Read Later",
            account=crud.user.get(session, user_id),
            commit=commit,
            info={
                "read_now_count": len(list(read_now_orm.items)),
                "read_next_count": len(list(read_next_orm.items)),
            },
        )

        return read_now_orm, read_next_orm
