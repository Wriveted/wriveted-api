from typing import Dict, Literal

from pydantic import BaseModel, validator
from app.schemas.labelset import CharacterKey, GenreKey, WritingStyleKey

from app.schemas.recommendations import HueKeys, ReadingAbilityKey


class GptWorkData(BaseModel):
    short_summary: str | None
    long_summary: str | None

    lexile: str | None
    reading_ability: list[ReadingAbilityKey] | None = []

    styles: list[WritingStyleKey] | None = []
    genres: list[GenreKey] | None = []

    hue_map: Dict[HueKeys, float] | None = {}
    hues: list[HueKeys] | None = []

    @validator("hues", pre=True)
    def generate_hues(cls, value, values):
        hue_map = values.get("hue_map")
        if hue_map is None:
            return value

        # grab top ..3 hues
        hues = [k for k, _v in sorted(hue_map.items(), key=lambda item: -item[1])[:3]]

        if not hues:
            raise ValueError("No hues found")

        return hues

    characters: list[CharacterKey] | None = []
    gender: Literal["male", "female", "nonbinary", "unknown"] | None = None

    series: str | None
    series_number: int | None
    awards: list[str] | None = []
    notes: str | None


class GptUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class GptLabelResponse(BaseModel):
    system_prompt: str
    user_content: str
    output: GptWorkData | str
    usage: GptUsage | None
