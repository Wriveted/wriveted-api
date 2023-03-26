import enum
from pydantic import AnyHttpUrl, BaseModel

from app.schemas import CaseInsensitiveStringEnum


class LinkBrief(BaseModel):
    class LinkType(str, enum.Enum):
        RETAILER = "retailer"
        REVIEW = "review"

    type: LinkType = LinkType.RETAILER
    url: AnyHttpUrl
    retailer: str = "Amazon AU"
