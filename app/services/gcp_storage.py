from base64 import b64decode

from google.cloud import storage
from google.api_core.exceptions import NotFound
from structlog import get_logger

from app.config import get_settings

settings = get_settings()
logger = get_logger()

# setup gcp bucket
def get_gcp_bucket(bucket_name: str):
    """
    Populate a google bucket object from the bucket name.
    """
    # get the bucket
    storage_client = storage.Client()
    return storage_client.get_bucket(bucket_name)


# upload base64 image string to google bucket
def base64_string_to_bucket(data: str, folder: str, filename: str, bucket_name: str):
    """
    Upload a base64 image string to the specified google bucket, returning the public url.
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
    bucket = get_gcp_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(data_bytes, content_type=f"image/{filetype}")

    # return the public url to the image
    return blob.public_url


def url_to_blob_name(url: str) -> str:
    """
    Convert a gcp storage url to a blob name.
    We can just find "the slash after 'storage.googleapis.com/'" and split on that.
    """
    anchor = "storage.googleapis.com/"
    try:
        return url.split(anchor, 1)[-1].split("/", 1)[-1]
    except IndexError:
        return None


def delete_blob(bucket_name: str, blob_name: str):
    """
    Delete a blob from the bucket.
    """
    bucket = get_gcp_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.delete()


def get_blob(bucket_name: str, blob_name: str) -> Blob:
    """
    Get a blob from the bucket. Raises a google.api_core.exceptions.NotFound exception if the blob doesn't exist.
    """
    bucket = get_gcp_bucket(bucket_name)
    blob = bucket.blob(blob_name)

    if not blob.exists():
        raise NotFound(f"Blob {blob_name} doesn't exist")

    return blob
