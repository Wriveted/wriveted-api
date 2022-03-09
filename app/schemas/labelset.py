from tkinter import Label
from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from app.models.labelset import LabelOrigin, RecommendStatus
from app.schemas.genre import Genre
from app.schemas.hue import Hue
from uuid import UUID

class LabelSetBrief(BaseModel):
    id:        str
    work_id:   str
    work_name: str

    class Config:
        orm_mode = True


class LabelSetDetail(LabelSetBrief):
    hues:                    list[Hue]
    hue_origin:              Optional[LabelOrigin]

    min_age:                 Optional[int]
    max_age:                 Optional[int]
    age_origin:              Optional[LabelOrigin]
    reading_ability_keys:    Optional[list[str]]
    reading_ability_origin:  Optional[LabelOrigin]

    genres:                  list[Genre]

    huey_summary:            Optional[str]
    summary_origin:          Optional[LabelOrigin]

    labelled_by_user_id:     Optional[UUID]
    labelled_by_sa_id:       Optional[UUID]
    info:                    Optional[dict]

    recommend_status:        Optional[RecommendStatus]
    recommend_status_origin: Optional[RecommendStatus]
    checked:                 Optional[bool]

    created_at:              datetime
    updated_at:              Optional[datetime]


# everything is optional here. also used for patch requests
class LabelSetCreateIn(BaseModel):
    hue_primary_key:         Optional[str]
    hue_secondary_key:       Optional[str]
    hue_tertiary_key:        Optional[str]
    hue_origin:              Optional[LabelOrigin]

    min_age:                 Optional[int]
    max_age:                 Optional[int]
    age_origin:              Optional[LabelOrigin]
    reading_ability_keys:    Optional[list[str]]
    reading_ability_origin:  Optional[LabelOrigin]

    huey_summary:            Optional[str]
    summary_origin:          Optional[LabelOrigin]

    genres:                  Optional[list[Genre]]

    labelled_by_user_id:     Optional[UUID]
    labelled_by_sa_id:       Optional[UUID]
    info:                    Optional[dict]

    recommend_status:        Optional[RecommendStatus]
    recommend_status_origin: Optional[LabelOrigin]
    checked:                 Optional[bool]


class LabelSetPatch(BaseModel):
    isbn:         str
    patch_data:   LabelSetCreateIn
    huey_pick:    bool