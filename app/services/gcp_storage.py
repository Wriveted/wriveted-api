from base64 import b64decode
from google.cloud import storage
from structlog import get_logger

from app.config import get_settings

settings = get_settings()
logger = get_logger()

# setup gcp bucket
def get_cover_image_bucket():

    """
    Get the google bucket for cover images.
    """
    # get the bucket name
    bucket_name = settings.GCP_IMAGE_BUCKET

    # get the bucket
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)

    # return the bucket
    return bucket


# upload base64 image string to google bucket
def base64_string_to_bucket(data: str, folder: str, filename: str):
    """
    Upload a base64 image string to the environment's google bucket, returning the public url
    """
    # get the image type
    filetype = data.split(";")[0].split("/")[1]

    # get the image data
    image_data = data.split(",")[1]
    data_bytes = b64decode(image_data)

    # create blob filename
    full_filename = f"{filename}.{filetype}"
    blob_name = f"{folder}/{full_filename}" if folder else full_filename

    # upload the image to the bucket
    bucket = get_cover_image_bucket()
    blob = bucket.blob(blob_name)
    blob.upload_from_string(data_bytes, content_type=f"image/{filetype}")

    # return the public url to the image
    return blob.public_url


def url_to_blob_name(url: str) -> str:
    """
    Convert a wriveted cover image url to a blob name.
    """
    return url.split(settings.GCP_IMAGE_BUCKET + "/")[1]


def delete_blob(blob_name: str):
    """
    Delete a blob from the bucket.
    """
    bucket = get_cover_image_bucket()
    blob = bucket.blob(blob_name)
    blob.delete()
