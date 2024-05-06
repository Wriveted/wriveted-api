from pydantic import BaseModel, ConfigDict


class SearchQueryInput(BaseModel):
    query: str
    # author_id: Optional[int] = None
    # type


class BookSearchResult(BaseModel):
    work_id: str
    author_ids: list[str]
    series_id: str | None

    work_title_headline: str
    work_subtitle_headline: str
    series_title_headline: str

    author_first_headline: str
    author_last_headline: str


class SearchResults(BaseModel):
    event_id: str

    input: SearchQueryInput
    books: list[BookSearchResult]

    model_config = ConfigDict(from_attributes=True)
