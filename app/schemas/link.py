from enum import Enum

from pydantic import AnyHttpUrl, BaseModel


class LinkBrief(BaseModel):
    class LinkType(str, Enum):
        RETAILER = "retailer"
        REVIEW = "review"

    type: LinkType = LinkType.RETAILER
    url: AnyHttpUrl
    retailer: str = "Amazon AU"
