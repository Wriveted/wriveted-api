from typing import Optional, Any

from pydantic import BaseModel
from datetime import datetime

from app.models.labelset import DoeCode, ReadingAbility
from app.schemas.genre import Genre
from app.schemas.hue import Hue


class LabelSetBrief(BaseModel):
    id: str
    work_id: str
    work_name: str

    class Config:
        orm_mode = True


class LabelSetDetail(LabelSetBrief):
    hues: list[Hue]
    reading_ability: ReadingAbility
    doe_code: DoeCode
    min_age: int
    max_age: int
    lexile: str
    labelled_by_user_id: Optional[int]
    labelled_by_sa_id: Optional[int]
    info: Optional[dict]
    genres: list[Genre]
    checked: bool
    created_at: datetime
    updated_at: Optional[datetime]


# this is only for the case where the partial/patch method doesn't work:
# https://fastapi.tiangolo.com/tutorial/body-updates/#partial-updates-with-patch
class LabelSetCreateIn(BaseModel):
    hue_primary_id: Optional[int]
    hue_secondary_id: Optional[int]
    hue_tertiary_id: Optional[int]
    reading_ability: Optional[ReadingAbility]
    doe_code: Optional[DoeCode]
    min_age: Optional[int]
    max_age: Optional[int]
    lexile: Optional[str]
    labelled_by_user_id: Optional[int]
    labelled_by_sa_id: Optional[int]
    info: Optional[dict]
    genres: list[Genre]
