from uuid import UUID
from app import crud
from sqlalchemy.orm import Session
from app.schemas.recommendations import ReadingAbilityKey
from app.schemas.booklist import (
    BookListCreateIn,
    BookListItemCreateIn,
    BookListItemInfo,
)
from app.models.booklist import ListType
from app.schemas.users.huey_attributes import HueyAttributes
from app.services.recommendations import get_recommended_labelset_query


def generate_reading_pathway_lists(
    session: Session, user_id: UUID, attributes: HueyAttributes
):
    """
    Generate booklists `Books to read now` and `Books to read next` for the provided user,
    populating each with 10 appropriate books based on the provided `huey_attributes`
    """

    try:
        current_reading_ability = attributes.reading_ability[0]
    except (ValueError, TypeError, IndexError):
        return

    current_reading_ability_key = current_reading_ability.name

    # Get the read now list by generating 10 books via standard recommendation
    read_now_query = get_recommended_labelset_query(
        session,
        hues=attributes.hues,
        age=attributes.age,
        reading_abilities=[current_reading_ability_key],
    )

    # Get the read next list by incrementing the reading ability and doing the same

    # since ReadingAbilityKey is a 3.7+ enum.Enum type, it remembers natural definition order
    # we can treat this as defacto indexing (allowing us to increment or decrement a reading ability)
    reading_ability_key_list = [
        v.name
        for v in ReadingAbilityKey.__dict__.values()
        if isinstance(v, ReadingAbilityKey)
    ]
    current_reading_ability_index = reading_ability_key_list.index(
        current_reading_ability_key
    )

    # but don't increment more than the highest level. harry_potter + 1 = harry_potter
    next_reading_ability_index = min(
        len(reading_ability_key_list) - 1, current_reading_ability_index + 1
    )

    read_next_query = get_recommended_labelset_query(
        session,
        hues=attributes.hues,
        age=attributes.age,
        reading_abilities=[reading_ability_key_list[next_reading_ability_index]],
    )

    now_results = session.execute(read_now_query.limit(10)).all()
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

    next_results = session.execute(read_next_query.limit(10)).all()
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

    crud.booklist.create(session, obj_in=read_now_booklist_data)
    crud.booklist.create(session, obj_in=read_next_booklist_data)

    crud.event.create(
        session,
        title="Created reading pathway lists",
        description="Created Books To Read Now and Books To Read Later",
        account=crud.user.get(session, user_id),
    )
