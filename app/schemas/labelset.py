from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from app.models.labelset import ReadingAbility, RecommendStatus
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
    hues:                list[Hue]

    min_age:             Optional[int]
    max_age:             Optional[int]
    reading_ability:     Optional[ReadingAbility]

    labelled_by_user_id: Optional[UUID]
    labelled_by_sa_id:   Optional[UUID]
    info:                Optional[dict]

    recommend_status:    Optional[RecommendStatus]
    checked:             Optional[bool]

    created_at:          datetime
    updated_at:          Optional[datetime]


# everything is optional here. also used for patch requests
class LabelSetCreateIn(BaseModel):
    hue_primary_id:      Optional[int]
    hue_secondary_id:    Optional[int]
    hue_tertiary_id:     Optional[int]

    min_age:             Optional[int]
    max_age:             Optional[int]
    reading_ability:     Optional[ReadingAbility]

    labelled_by_user_id: Optional[UUID]
    labelled_by_sa_id:   Optional[UUID]
    info:                Optional[dict]

    recommend_status:    Optional[RecommendStatus]
    checked:             Optional[bool]