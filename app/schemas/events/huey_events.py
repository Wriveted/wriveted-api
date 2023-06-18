from pydantic import BaseModel


class HueyEventsSharedInfo(BaseModel):
    chatbot: str | None
    experiments: dict[str, bool] | None
    school_name: str | None
    distinct_id: str | None


class HueyBookReviewedInfo(HueyEventsSharedInfo):
    isbn: str | None
    read: bool
    image: str | None
    liked: bool
    title: str | None
    author: str | None
