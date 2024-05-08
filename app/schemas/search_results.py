from pydantic import BaseModel, ConfigDict

from app.schemas.work import WorkBrief


class SearchQueryInput(BaseModel):
    query: str | None = None
    author_id: int | None = None
    # type


class SearchResults(BaseModel):
    input: SearchQueryInput
    books: list[WorkBrief]

    model_config = ConfigDict(from_attributes=True)
