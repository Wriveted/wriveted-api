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

    min_age:             int | None
    max_age:             int | None
    reading_ability:     ReadingAbility | None

    labelled_by_user_id: UUID | None
    labelled_by_sa_id:   UUID | None
    info:                dict | None

    recommend_status:    RecommendStatus | None
    checked:             bool | None

    created_at:          datetime
    updated_at:          datetime | None


# everything is optional here. also used for patch requests
class LabelSetCreateIn(BaseModel):
    hue_primary_id:      int | None
    hue_secondary_id:    int | None
    hue_tertiary_id:     int | None

    min_age:             int | None
    max_age:             int | None
    reading_ability:     ReadingAbility | None

    labelled_by_user_id: UUID | None
    labelled_by_sa_id:   UUID | None
    info:                dict | None

    recommend_status:    RecommendStatus | None
    checked:             bool | None