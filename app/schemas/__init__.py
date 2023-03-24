from base64 import b64decode
from binascii import Error as BinasciiError
import enum
from io import BytesIO
from urllib import parse

from PIL import Image
from structlog import get_logger

logger = get_logger()


class CaseInsensitiveStringEnum(str, enum.Enum):
    @classmethod
    def _missing_(cls, name):
        for member in cls:
            if member.name.lower() == name.lower():
                return member


def is_url(value: str) -> bool:
    try:
        result = parse.urlparse(value)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


def validate_image_url_or_base64_string(
    v: str,
    field_name: str,
    max_size: int = 512_000,
    min_width: int = 100,
    max_width: int = 2000,
    min_height: int = 100,
    max_height: int = 2000,
) -> callable:
    """
    Validate that the input field is either a URL or a valid base64-encoded image string, properly formed.

    - If a URL is passed, the function will not check if the URL is reachable or the image is valid.
    - If a base64-encoded image string is passed, the function will remove the metadata from the string before decoding it to an image.

    The function will validate the following for base64-encoded image strings:
    - The maximum image size is `max_size` bytes.
    - The image format is either `jpg`, `jpeg`, or `png`.
    - The image dimensions are within the minimum and maximum width and height provided.

    Raises a `ValueError` if the input is not a valid image URL or base64-encoded image string.
    """
    if not v:
        return

    logger.debug(f"Validating {field_name} `{v[0:100]}...`")

    # check if v is a URL
    if is_url(str(v)):
        # if it's a URL, we skip the image download and just return the URL
        return v

    # v is now hopefully a base64 string
    try:
        # remove the metadata from the base64 string before decoding
        raw_image_bytes = b64decode(v.split(",")[1])
        img = Image.open(BytesIO(raw_image_bytes))
    except (BinasciiError, IOError) as e:
        raise ValueError(
            f"{field_name} must be a valid base64 image string, properly formed"
        )

    # image filesize
    if len(raw_image_bytes) > max_size:
        raise ValueError(f"Maximum {field_name} size is {max_size/1024}kb")

    # image formats
    if img.format.lower() not in ["jpg", "jpeg", "png"]:
        raise ValueError(f"{field_name} must be either `jpg`, `jpeg`, or `png` format")

    # image dimensions
    width, height = img.size
    if (
        (width < min_width)
        or (height < min_height)
        or (width > max_width)
        or (height > max_height)
    ):
        raise ValueError(
            f"Minimum {field_name} dimensions are {min_width}x{min_height} and maximum dimensions are {max_width}x{max_height}"
        )

    # we now have a valid image base64 string that points to an image
    return v
