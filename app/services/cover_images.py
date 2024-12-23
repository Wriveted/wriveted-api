from uuid import uuid4

from structlog import get_logger

from app.config import get_settings
from app.models.collection_item import CollectionItem
from app.models.edition import Edition
from app.services.gcp_storage import (
    base64_string_to_bucket,
    delete_blob,
    url_to_blob_name,
)

settings = get_settings()
logger = get_logger()


def _handle_upload_collection_item_cover_image(
    image_data: str,
    collection_id: str,
    edition_isbn: str | None,
) -> str:
    """
    Handle a cover image upload for a private collection item (not a public edition).
    """
    # generate folder and filename
    folder = f"private/{collection_id}"
    filename = edition_isbn or str(uuid4())

    # upload the image to the bucket
    public_url = base64_string_to_bucket(
        data=image_data,
        folder=folder,
        filename=filename,
        bucket_name=settings.GCP_IMAGE_BUCKET,
    )

    return public_url


def handle_collection_item_cover_image_update(
    collection_item: CollectionItem, image_data: str
) -> str | None:
    """
    Handle a cover image update for an existing collection item.
    If image_data is empty, purges any existing image from gcp and the db object.
    If the image is new, deletes the old image from gcp.
    """
    new_url = (
        _handle_upload_collection_item_cover_image(
            image_data,
            str(collection_item.collection_id),
            collection_item.edition_isbn,
        )
        if image_data
        else None
    )
    if collection_item.cover_image_url and collection_item.cover_image_url != new_url:
        delete_blob(
            settings.GCP_IMAGE_BUCKET,
            url_to_blob_name(
                settings.GCP_IMAGE_BUCKET, collection_item.cover_image_url
            ),
        )
    return new_url


def handle_new_collection_item_cover_image(
    collection_id: str, edition_isbn: str | None, image_data: str
) -> str | None:
    """
    Handle a cover image upload for a new collection item.
    """
    return _handle_upload_collection_item_cover_image(
        image_data, collection_id, edition_isbn
    )


def _handle_upload_edition_cover_image(
    image_data: str,
    edition_isbn: str,
    folder: str = "wriveted",
) -> str:
    """
    Handle a cover image upload for a public edition.
    """
    # upload the image to the bucket
    public_url = base64_string_to_bucket(
        data=image_data,
        folder=folder,
        filename=edition_isbn,
        bucket_name=settings.GCP_IMAGE_BUCKET,
    )

    return public_url


def handle_new_edition_cover_image(
    edition_isbn: str, image_data: str, folder: str | None
) -> str | None:
    """
    Handle a cover image upload for a new edition.
    """
    return _handle_upload_edition_cover_image(image_data, edition_isbn, folder)


def handle_edition_cover_image_update(
    edition: Edition, image_data: str, folder: str | None
) -> str | None:
    """
    Handle a cover image update for an existing edition.
    If image_data is empty, purges any existing image from gcp and the db object.
    If the image is new, deletes the old image from gcp.
    """
    new_url = (
        _handle_upload_edition_cover_image(
            image_data,
            edition.isbn,
            folder,
        )
        if image_data
        else None
    )
    if edition.cover_url and edition.cover_url != new_url:
        delete_blob(
            settings.GCP_IMAGE_BUCKET,
            url_to_blob_name(settings.GCP_IMAGE_BUCKET, edition.cover_url),
        )
    return new_url
