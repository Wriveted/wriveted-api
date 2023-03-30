from typing import Dict, Literal

from pydantic import BaseModel, root_validator, validator

from app.models.labelset import RecommendStatus
from app.schemas.labelset import CharacterKey, GenreKey, WritingStyleKey
from app.schemas.recommendations import HueKeys, ReadingAbilityKey


class GptWorkData(BaseModel):
    short_summary: str | None
    long_summary: str | None

    reading_ability: list[ReadingAbilityKey] = []

    @validator("reading_ability", pre=True)
    def validate_reading_ability(cls, value):
        errors = []
        for item in value:
            try:
                _item = ReadingAbilityKey(item)
            except ValueError:
                permitted = ", ".join([e.name for e in ReadingAbilityKey])
                errors.append(
                    f"|'{item}' is not a valid Reading Ability Key. permitted Reading Ability Keys: [{permitted}]|"
                )
        if errors:
            raise ValueError(errors)
        return value

    styles: list[WritingStyleKey] | None = []

    @validator("styles", pre=True)
    def validate_styles(cls, value):
        errors = []
        for item in value:
            try:
                _item = WritingStyleKey(item)
            except ValueError:
                permitted = ", ".join([e.name for e in WritingStyleKey])
                errors.append(
                    f"|'{item}' is not a valid Style Key. permitted Style Keys: [{permitted}]|"
                )
        if errors:
            raise ValueError(errors)
        return value

    genres: list[GenreKey] | None = []

    @validator("genres", pre=True)
    def validate_genres(cls, value):
        errors = []
        for item in value:
            try:
                _item = GenreKey(item)
            except ValueError:
                permitted = ", ".join([e.name for e in GenreKey])
                errors.append(
                    f"|'{item}' is not a valid Genre Key. permitted Genre Keys: [{permitted}]|"
                )
        if errors:
            raise ValueError(errors)
        return value

    hue_map: Dict[HueKeys, float] = {}

    @validator("hue_map", pre=True)
    def validate_hue_map(cls, value):
        errors = []
        for key in value.keys():
            try:
                _item = HueKeys(key)
            except ValueError:
                permitted = ", ".join([e.name for e in HueKeys])
                errors.append(
                    f"|'{key}' is not a valid Hue Key. permitted Hue Keys: [{permitted}]|"
                )
        if errors:
            raise ValueError(errors)
        return value

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

        if max(hue_map.values()) < 0.2:
            raise ValueError(
                "Low values in hue_map. Are you sure you're assessing each value individually?"
            )

        if not hues:
            raise ValueError("No hues found in hue_map. Must include non-zero values.")

        return hues

    characters: list[CharacterKey] | None = []

    @validator("characters", pre=True)
    def validate_characters(cls, value):
        errors = []
        for item in value:
            try:
                _item = CharacterKey(item)
            except ValueError:
                permitted = ", ".join([e.name for e in CharacterKey])
                errors.append(
                    f"|'{item}' is not a valid Character Key. permitted Character Keys: [{permitted}]|"
                )
        if errors:
            raise ValueError(errors)
        return value

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
    recommend_status: RecommendStatus
    controversial_themes: list[str] | None = []


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

        for usage_dict in values["usages"]:
            if isinstance(usage_dict, GptPromptUsage):
                usage = usage_dict
            else:
                usage = GptPromptUsage(**usage_dict)

            overall_prompt_tokens += usage.prompt_tokens
            overall_completion_tokens += usage.completion_tokens
            overall_total_tokens += usage.total_tokens
            overall_duration += usage.duration

        values["overall_prompt_tokens"] = overall_prompt_tokens
        values["overall_completion_tokens"] = overall_completion_tokens
        values["overall_total_tokens"] = overall_total_tokens
        values["overall_duration"] = round(overall_duration, 2)

        return values

    def __repr__(self) -> str:
        return (
            f"Prompt tokens: {self.overall_prompt_tokens}, "
            f"Completion tokens: {self.overall_completion_tokens}, "
            f"Total tokens: {self.overall_total_tokens}, "
            f"Duration: {self.overall_duration:.2f}, "
            f"Prompts: {len(self.usages)}"
        )


class GptLabelResponse(BaseModel):
    system_prompt: str
    user_content: str
    output: GptWorkData
    usage: GptUsage
