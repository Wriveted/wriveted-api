import enum
from urllib import parse

from structlog import get_logger

logger = get_logger()


class CaseInsensitiveStringEnum(str, enum.Enum):
    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            # attempt case-insensitive lookup
            for member in cls:
                if member.name.lower() == value.lower():
                    return member

        # fallback to default behavior if lookup fails or if value is not a string
        return None


def is_url(value: str) -> bool:
    try:
        result = parse.urlparse(value)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False
