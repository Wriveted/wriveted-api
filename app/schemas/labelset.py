from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.labelset import LabelOrigin, RecommendStatus
from app.schemas.hue import Hue


class ReadingAbility(BaseModel):
    id: str
    key: str
    name: str

    class Config:
        orm_mode = True


class LabelSetBrief(BaseModel):
    id: str
    work_id: str
    # work_name: str

    class Config:
        orm_mode = True


class LabelSetBasic(LabelSetBrief):
    hues: list[Hue]
    min_age: Optional[int]
    max_age: Optional[int]
    reading_abilities: list[ReadingAbility]
    huey_summary: Optional[str]


class LabelSetDetail(LabelSetBrief):
    hues: list[Hue]
    hue_origin: Optional[LabelOrigin]

    min_age: Optional[int]
    max_age: Optional[int]
    age_origin: Optional[LabelOrigin]

    reading_abilities: list[ReadingAbility]
    reading_ability_origin: Optional[LabelOrigin]

    huey_summary: Optional[str]
    summary_origin: Optional[LabelOrigin]

    labelled_by_user_id: Optional[UUID]
    labelled_by_sa_id: Optional[UUID]
    info: Optional[dict]

    recommend_status: Optional[RecommendStatus]
    recommend_status_origin: Optional[LabelOrigin]
    checked: Optional[bool]

    created_at: datetime
    updated_at: Optional[datetime]


# everything is optional here. also used for patch requests
class LabelSetCreateIn(BaseModel):
    hue_primary_key: Optional[str]
    hue_secondary_key: Optional[str]
    hue_tertiary_key: Optional[str]
    hue_origin: Optional[LabelOrigin]

    min_age: Optional[int]
    max_age: Optional[int]
    age_origin: Optional[LabelOrigin]
    reading_ability_keys: Optional[list[str]]
    reading_ability_origin: Optional[LabelOrigin]

    huey_summary: Optional[str]
    summary_origin: Optional[LabelOrigin]

    labelled_by_user_id: Optional[UUID]
    labelled_by_sa_id: Optional[UUID]
    info: Optional[dict]

    recommend_status: Optional[RecommendStatus]
    recommend_status_origin: Optional[LabelOrigin]
    checked: Optional[bool]

    def empty(self):
        for att in self.__dict__:
            if getattr(self, att):
                return False
        return True


class LabelSetPatch(BaseModel):
    isbn: str
    patch_data: LabelSetCreateIn
    huey_pick: bool
