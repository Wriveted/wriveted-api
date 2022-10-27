import enum
import uuid
from typing import Optional

from pydantic import BaseModel, HttpUrl

from app.schemas.labelset import LabelSetDetail


class ReadingAbilityKey(str, enum.Enum):
    SPOT = "SPOT"
    CAT_HAT = "CAT_HAT"
    TREEHOUSE = "TREEHOUSE"
    CHARLIE_CHOCOLATE = "CHARLIE_CHOCOLATE"
    HARRY_POTTER = "HARRY_POTTER"


class HueKeys(str, enum.Enum):
    hue01_dark_suspense = "hue01_dark_suspense"
    hue02_beautiful_whimsical = "hue02_beautiful_whimsical"
    hue03_dark_beautiful = "hue03_dark_beautiful"
    hue05_funny_comic = "hue05_funny_comic"
    hue06_dark_gritty = "hue06_dark_gritty"
    hue07_silly_charming = "hue07_silly_charming"
    hue08_charming_inspiring = "hue08_charming_inspiring"
    hue09_charming_playful = "hue09_charming_playful"
    hue10_inspiring = "hue10_inspiring"
    hue11_realistic_hope = "hue11_realistic_hope"
    hue12_funny_quirky = "hue12_funny_quirky"
    hue13_straightforward = "hue13_straightforward"


class HueyRecommendationFilterBase(BaseModel):
    hues: Optional[list[HueKeys]] = None
    age: Optional[int] = None
    reading_abilities: Optional[list[ReadingAbilityKey]] = None
    recommendable_only: Optional[bool] = None
    exclude_isbns: Optional[list[str]] = None
    fallback: Optional[bool] = None
    # hueys_picks: Optional[bool]


class HueyRecommendationFilter(HueyRecommendationFilterBase):
    wriveted_identifier: Optional[uuid.UUID] = None
    dedupe_authors: bool = True


class HueyRecommendationFilterUsed(HueyRecommendationFilterBase):
    school_id: Optional[int] = None


class HueyBook(BaseModel):
    work_id: int
    isbn: str
    cover_url: HttpUrl | None
    display_title: str  # {leading article} {title} (leading article is optional, thus bridging whitespace optional)
    authors_string: str  # {a1.first_name} {a1.last_name}, {a2.first_name} {a2.last_name} ... (first name is optional, thus bridging whitespace optional)
    summary: str
    labels: LabelSetDetail


class HueyOutput(BaseModel):
    count: int
    books: list[HueyBook]
    # query: dict[str, str | list[str] | None]
    query: HueyRecommendationFilterUsed
