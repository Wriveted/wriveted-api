from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.labelset import LabelOrigin, RecommendStatus
from app.schemas import CaseInsensitiveStringEnum
from app.schemas.hue import Hue
from app.schemas.recommendations import ReadingAbilityKey


class WritingStyleKey(CaseInsensitiveStringEnum):
    DARK = "DARK"
    LIGHT = "LIGHT"
    FUNNY = "FUNNY"
    SERIOUS = "SERIOUS"
    QUIRKY = "QUIRKY"
    ACTION_PACKED = "ACTION_PACKED"
    WHIMSICAL = "WHIMSICAL"
    BEAUTIFUL = "BEAUTIFUL"
    CHARMING = "CHARMING"
    GRIM = "GRIM"
    INSPIRING = "INSPIRING"
    CALM = "CALM"
    SUSPENSEFUL = "SUSPENSEFUL"
    SILLY = "SILLY"
    PLAYFUL = "PLAYFUL"
    REALISTIC = "REALISTIC"
    INFORMATIVE = "INFORMATIVE"


class ControversialThemeKey(CaseInsensitiveStringEnum):
    VIOLENT = "VIOLENT"
    SEXUAL = "SEXUAL"
    DRUGS = "DRUGS"
    RELIGIOUS = "RELIGIOUS"
    LGBTQI = "LGBTQI"
    PROFANITY = "PROFANITY"
    MENTAL_HEALTH = "MENTAL_HEALTH"
    OTHER = "OTHER"


class GenreKey(CaseInsensitiveStringEnum):
    FACTUAL_NON_FICTION = "FACTUAL_NON_FICTION"
    FUNNY = "FUNNY"
    ROMANCE = "ROMANCE"
    SCIENCE = "SCIENCE"
    SCIFI = "SCIFI"
    CLASSIC_FICTION = "CLASSIC_FICTION"
    HISTORICAL = "HISTORICAL"
    FANTASY = "FANTASY"
    FAIRYTALES = "FAIRYTALES"
    HORROR_SPOOKY = "HORROR_SPOOKY"
    MYSTERY_SUSPENSE = "MYSTERY_SUSPENSE"
    ADVENTURE_AND_ACTION = "ADVENTURE_AND_ACTION"
    CRIME = "CRIME"
    RHYMES_POETRY = "RHYMES_POETRY"
    BIOGRAPHICAL = "BIOGRAPHICAL"
    GRAPHIC_NOVELS = "GRAPHIC_NOVELS"
    WAR = "WAR"
    DYSTOPIAN = "DYSTOPIAN"
    AUSTRALIAN = "AUSTRALIAN"
    AMERICAN = "AMERICAN"
    BRITISH = "BRITISH"
    INDIGENOUS = "INDIGENOUS"
    SPORTS = "SPORTS"
    PICTURE_BOOK = "PICTURE_BOOK"
    YOUNG_ADULT = "YOUNG_ADULT"
    LGBTQ = "LGBTQ"


class CharacterKey(CaseInsensitiveStringEnum):
    BUGS = "BUGS"
    CATS_DOGS_AND_MICE = "CATS_DOGS_AND_MICE"
    HORSES_AND_FARM_ANIMALS = "HORSES_AND_FARM_ANIMALS"
    OCEAN_CREATURES = "OCEAN_CREATURES"
    WOLVES_AND_WILD_ANIMALS = "WOLVES_AND_WILD_ANIMALS"
    AUSTRALIAN_ANIMALS = "AUSTRALIAN_ANIMALS"
    BRITISH_ANIMALS = "BRITISH_ANIMALS"
    AMERICAN_ANIMALS = "AMERICAN_ANIMALS"
    DINOSAURS = "DINOSAURS"
    PRINCESSES_FAIRIES_MERMAIDS = "PRINCESSES_FAIRIES_MERMAIDS"
    UNICORNS = "UNICORNS"
    SUPERHEROES = "SUPERHEROES"
    FAMILIES_AND_FRIENDS = "FAMILIES_AND_FRIENDS"
    MONSTERS_GHOSTS_AND_VAMPIRES = "MONSTERS_GHOSTS_AND_VAMPIRES"
    ALIENS = "ALIENS"
    TRAINS_CARS_AND_TRUCKS = "TRAINS_CARS_AND_TRUCKS"
    MISFITS_AND_UNDERDOGS = "MISFITS_AND_UNDERDOGS"
    PIRATES = "PIRATES"
    ROBOTS = "ROBOTS"
    ATHLETES_AND_SPORT_STARS = "ATHLETES_AND_SPORT_STARS"
    WITCHES_WIZARDS_MAGIC = "WITCHES_WIZARDS_MAGIC"


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
    reading_ability_keys: Optional[list[ReadingAbilityKey]]
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
