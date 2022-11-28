import os
from google.cloud import storage

from app.config import get_settings

settings = get_settings()

# setup gcp bucket
def get_cover_image_bucket():

    """
    Get the google bucket for cover images.
    """
    # get the bucket name
    bucket_name = settings.GCP_IMAGE_BUCKET_NAME

    # get the bucket
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)

    # return the bucket
    return bucket


# upload base64 image string to google bucket
def base64_string_to_bucket(data: str, folder: str, filename: str):
    """
    Upload a base64 image string to the environment's google bucket.
    """
    # get the image type
    filetype = data.split(";")[0].split("/")[1]

    # get the image data
    image_data = data.split(",")[1]

    # create blob filename
    full_filename = f"{filename}.{filetype}"
    blob_name = f"{folder}/{full_filename}" if folder else full_filename

    # upload the image to the bucket
    bucket = get_cover_image_bucket()
    blob = bucket.blob(blob_name)
    blob.upload_from_string(image_data, content_type=f"image/{filetype}")

    # return the public url to the image
    return blob.public_url
