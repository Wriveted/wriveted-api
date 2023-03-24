from typing import Dict, Literal

from pydantic import BaseModel, root_validator, validator
from app.schemas.labelset import CharacterKey, GenreKey, WritingStyleKey

from app.schemas.recommendations import HueKeys, ReadingAbilityKey


class GptWorkData(BaseModel):
    short_summary: str | None
    long_summary: str | None

    reading_ability: list[ReadingAbilityKey] = []

    styles: list[WritingStyleKey] | None = []
    genres: list[GenreKey] | None = []

    hue_map: Dict[HueKeys, float] = {}
    hues: list[HueKeys] = []

    @validator("hues", always=True, pre=True)
    def generate_hues(cls, value, values):
        hue_map = values.get("hue_map")

        if not hue_map:
            return value

        # grab top ..3 hues with value > 0.1
        hues = [
            k
            for k, v in sorted(hue_map.items(), key=lambda item: -item[1])[:3]
            if v > 0.1
        ]

        if not hues:
            raise ValueError("No hues found in map")

        return hues

    characters: list[CharacterKey] | None = []
    gender: Literal["male", "female", "nonbinary", "unknown"] | None = None

    series: str | None
    series_number: int | None

    @validator("series_number", pre=True)
    def series_number_to_int(cls, value):
        if value is None:
            return None

        try:
            return int(value)
        except ValueError:
            return None

    awards: list[str] | None = []
    notes: str | None


class GptPromptUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    duration: float


class GptPromptResponse(BaseModel):
    usage: GptPromptUsage
    output: str


class GptUsage(BaseModel):
    overall_prompt_tokens: int
    overall_completion_tokens: int
    overall_total_tokens: int
    overall_duration: float
    usages: list[GptPromptUsage]

    # calculate the overall usage from the list
    @root_validator(pre=True)
    def calculate_overall_usage(cls, values):
        overall_prompt_tokens = 0
        overall_completion_tokens = 0
        overall_total_tokens = 0
        overall_duration = 0

        for usage in values["usages"]:
            overall_prompt_tokens += usage.prompt_tokens
            overall_completion_tokens += usage.completion_tokens
            overall_total_tokens += usage.total_tokens
            overall_duration += usage.duration

        values["overall_prompt_tokens"] = overall_prompt_tokens
        values["overall_completion_tokens"] = overall_completion_tokens
        values["overall_total_tokens"] = overall_total_tokens
        values["overall_duration"] = overall_duration

        return values

    def __repr__(self) -> str:
        return (
            f"Prompt tokens: {self.overall_prompt_tokens}, "
            f"Completion tokens: {self.overall_completion_tokens}, "
            f"Total tokens: {self.overall_total_tokens}, "
            f"Duration: {self.overall_duration}, "
            f"Prompts: {len(self.usages)}"
        )


class GptLabelResponse(BaseModel):
    system_prompt: str
    user_content: str
    output: GptWorkData
    usage: GptUsage
