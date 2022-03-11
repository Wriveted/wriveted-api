from pydantic import BaseModel, HttpUrl


class HueyBook(BaseModel):
    isbn: str
    cover_url: HttpUrl | None
    display_title: str      # {leading article} {title} (leading article is optional, thus bridging whitespace optional)
    authors_string: str         # {a1.first_name} {a1.last_name}, {a2.first_name} {a2.last_name} ... (first name is optional, thus bridging whitespace optional)
    summary: str


class HueyOutput(BaseModel):
    count: int
    books: list[HueyBook]