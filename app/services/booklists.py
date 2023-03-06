from structlog import get_logger

import app.services as services
from app.config import get_settings
from app.db.session import get_session_maker
from app.models.booklist import BookList, ListType
from app.schemas.booklist import (
    BookListCreateIn,
    BookListItemCreateIn,
    BookListItemInfo,
)
from app.schemas.users.huey_attributes import HueyAttributes
from app.services.gcp_storage import (
    base64_string_to_bucket,
    delete_blob,
    url_to_blob_name,
)

logger = get_logger()
settings = get_settings()


def generate_reading_pathway_lists(
    user_id: str, attributes: HueyAttributes, limit: int = 100, commit: bool = True
):
    """
    Generate booklists `Books to read now` and `Books to read next` for the provided user,
    populating each with `limit` appropriate books based on the provided `huey_attributes`
    """

    from app import crud

    logger.info(
        "Creating reading pathway booklists for user",
        user_id=user_id,
        attributes=attributes,
        limit=limit,
    )

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
        read_now_query = services.recommendations.get_recommended_labelset_query(
            session,
            hues=attributes.hues,
            age=attributes.age,
            reading_abilities=[current_reading_ability_key],
        )

        # Get the read next list by incrementing the reading ability and doing the same
        next_reading_ability_key = services.recommendations.gen_next_reading_ability(
            current_reading_ability
        ).name
        read_next_query = services.recommendations.get_recommended_labelset_query(
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
                "attributes": attributes.dict(),
                "read_now_count": len(list(read_now_orm.items)),
                "read_next_count": len(list(read_next_orm.items)),
            },
        )

        return read_now_orm, read_next_orm


def _handle_upload_booklist_feature_image(
    image_data: str,
    booklist_id: str,
) -> str:
    """
    Handle a feature image upload for a public booklist.
    """
    # generate folder and filename
    folder = f"booklist-feature-images"
    filename = booklist_id

    # upload the image to the bucket
    public_url = base64_string_to_bucket(
        data=image_data,
        folder=folder,
        filename=filename,
        bucket_name=settings.GCP_HUEY_MEDIA_BUCKET,
    )

    return public_url


def handle_booklist_feature_image_update(
    booklist: BookList, image_data: str
) -> str | None:
    """
    Handle a feature image update for an existing booklist.
    If image_data is empty, purges any existing image from gcp and the db object.
    If the image is new, deletes the old image from gcp.
    """
    new_url = (
        _handle_upload_booklist_feature_image(
            image_data,
            str(booklist.id),
        )
        if image_data
        else None
    )
    current_url = booklist.info.get("image_url")
    if current_url and current_url != new_url:
        delete_blob(
            settings.GCP_IMAGE_BUCKET,
            url_to_blob_name(current_url),
        )
    return new_url


def handle_new_booklist_feature_image(booklist_id: str, image_data: str) -> str | None:
    """
    Handle a feature image upload for a new booklist.
    """
    return _handle_upload_booklist_feature_image(image_data, booklist_id)
