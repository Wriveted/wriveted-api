from pydantic import BaseModel, Field

from app.schemas.pagination import PaginatedResponse
from app.schemas.work import WorkBrief


class BookListItemInCollection(BaseModel):
    in_collection: bool
    work_id: str
    work_brief: WorkBrief
    editions_in_collection: list[str] = Field(
        ..., description="List of isbns associated with this work"
    )


class CollectionBookListIntersection(PaginatedResponse):
    """
    Comparison results between all items in a BookList with a library collection.
    """

    data: list[BookListItemInCollection]
