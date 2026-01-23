"""Unit tests for PreferenceQuestionContent and PreferenceAnswer Pydantic schemas.

Tests validation of preference/personality question content used in chatbot flows
for mapping user answers to reading preferences (hue dimensions).
"""

import pytest
from pydantic import ValidationError

from app.schemas.cms import PreferenceAnswer, PreferenceQuestionContent
from app.schemas.recommendations import HueKeys


class TestPreferenceAnswer:
    """Tests for PreferenceAnswer schema validation."""

    def test_valid_answer_with_all_fields(self):
        """Valid answer with text, image, and hue_map."""
        answer = PreferenceAnswer(
            text="The dark, mysterious door",
            image_url="https://example.com/door.png",
            hue_map={
                HueKeys.hue01_dark_suspense: 1.0,
                HueKeys.hue02_beautiful_whimsical: 0.5,
            },
        )
        assert answer.text == "The dark, mysterious door"
        assert answer.image_url == "https://example.com/door.png"
        assert answer.hue_map[HueKeys.hue01_dark_suspense] == 1.0

    def test_valid_answer_without_image(self):
        """Valid answer with just text and hue_map (image optional)."""
        answer = PreferenceAnswer(
            text="Adventure awaits!",
            hue_map={HueKeys.hue10_inspiring: 0.8},
        )
        assert answer.text == "Adventure awaits!"
        assert answer.image_url is None

    def test_empty_text_rejected(self):
        """Answer text cannot be empty."""
        with pytest.raises(ValidationError) as exc_info:
            PreferenceAnswer(
                text="",
                hue_map={HueKeys.hue01_dark_suspense: 0.5},
            )
        assert "String should have at least 1 character" in str(exc_info.value)

    def test_hue_weight_below_zero_rejected(self):
        """Hue weights must be >= 0.0."""
        with pytest.raises(ValidationError) as exc_info:
            PreferenceAnswer(
                text="Test answer",
                hue_map={HueKeys.hue01_dark_suspense: -0.1},
            )
        assert "must be between 0.0 and 1.0" in str(exc_info.value)

    def test_hue_weight_above_one_rejected(self):
        """Hue weights must be <= 1.0."""
        with pytest.raises(ValidationError) as exc_info:
            PreferenceAnswer(
                text="Test answer",
                hue_map={HueKeys.hue01_dark_suspense: 1.5},
            )
        assert "must be between 0.0 and 1.0" in str(exc_info.value)

    def test_hue_weight_boundary_values_accepted(self):
        """Boundary values 0.0 and 1.0 are valid."""
        answer = PreferenceAnswer(
            text="Boundary test",
            hue_map={
                HueKeys.hue01_dark_suspense: 0.0,
                HueKeys.hue02_beautiful_whimsical: 1.0,
            },
        )
        assert answer.hue_map[HueKeys.hue01_dark_suspense] == 0.0
        assert answer.hue_map[HueKeys.hue02_beautiful_whimsical] == 1.0

    def test_empty_hue_map_accepted(self):
        """Empty hue_map is technically valid (no preferences expressed)."""
        # This might be used for "skip" or "none of the above" options
        answer = PreferenceAnswer(
            text="None of these appeal to me",
            hue_map={},
        )
        assert answer.hue_map == {}

    def test_all_hue_keys_accepted(self):
        """All valid HueKeys are accepted."""
        all_hues = {key: 0.5 for key in HueKeys}
        answer = PreferenceAnswer(
            text="All hues",
            hue_map=all_hues,
        )
        assert len(answer.hue_map) == len(HueKeys)


class TestPreferenceQuestionContent:
    """Tests for PreferenceQuestionContent schema validation."""

    @pytest.fixture
    def valid_answers(self):
        """Fixture providing valid answer options."""
        return [
            PreferenceAnswer(
                text="Option A",
                hue_map={HueKeys.hue01_dark_suspense: 0.8},
            ),
            PreferenceAnswer(
                text="Option B",
                hue_map={HueKeys.hue02_beautiful_whimsical: 0.9},
            ),
        ]

    def test_valid_question_minimal(self, valid_answers):
        """Valid question with required fields only."""
        question = PreferenceQuestionContent(
            question_text="Which door will you choose?",
            answers=valid_answers,
        )
        assert question.question_text == "Which door will you choose?"
        assert question.min_age == 0  # Default
        assert question.max_age == 99  # Default
        assert len(question.answers) == 2

    def test_valid_question_with_age_range(self, valid_answers):
        """Valid question with explicit age targeting."""
        question = PreferenceQuestionContent(
            question_text="Which adventure sounds fun?",
            min_age=7,
            max_age=12,
            answers=valid_answers,
        )
        assert question.min_age == 7
        assert question.max_age == 12

    def test_empty_question_text_rejected(self, valid_answers):
        """Question text cannot be empty."""
        with pytest.raises(ValidationError) as exc_info:
            PreferenceQuestionContent(
                question_text="",
                answers=valid_answers,
            )
        assert "String should have at least 1 character" in str(exc_info.value)

    def test_single_answer_rejected(self):
        """At least 2 answer options are required."""
        with pytest.raises(ValidationError) as exc_info:
            PreferenceQuestionContent(
                question_text="Choose one:",
                answers=[
                    PreferenceAnswer(
                        text="Only option",
                        hue_map={HueKeys.hue01_dark_suspense: 0.5},
                    )
                ],
            )
        assert "at least 2" in str(exc_info.value).lower()

    def test_maximum_six_answers(self):
        """Maximum 6 answer options allowed."""
        answers = [
            PreferenceAnswer(
                text=f"Option {i}",
                hue_map={HueKeys.hue01_dark_suspense: 0.1 * i},
            )
            for i in range(7)
        ]
        with pytest.raises(ValidationError) as exc_info:
            PreferenceQuestionContent(
                question_text="Too many options:",
                answers=answers,
            )
        assert "at most 6" in str(exc_info.value).lower()

    def test_six_answers_accepted(self):
        """Exactly 6 answers is valid (boundary)."""
        answers = [
            PreferenceAnswer(
                text=f"Option {i}",
                hue_map={HueKeys.hue01_dark_suspense: 0.1 * i},
            )
            for i in range(1, 7)
        ]
        question = PreferenceQuestionContent(
            question_text="Many options:",
            answers=answers,
        )
        assert len(question.answers) == 6

    def test_two_answers_accepted(self):
        """Exactly 2 answers is valid (boundary)."""
        answers = [
            PreferenceAnswer(
                text="Yes",
                hue_map={HueKeys.hue01_dark_suspense: 1.0},
            ),
            PreferenceAnswer(
                text="No",
                hue_map={HueKeys.hue01_dark_suspense: 0.0},
            ),
        ]
        question = PreferenceQuestionContent(
            question_text="Binary choice:",
            answers=answers,
        )
        assert len(question.answers) == 2

    def test_duplicate_answer_text_rejected(self):
        """Answer texts must be unique within a question."""
        answers = [
            PreferenceAnswer(
                text="Same text",
                hue_map={HueKeys.hue01_dark_suspense: 0.8},
            ),
            PreferenceAnswer(
                text="Same text",
                hue_map={HueKeys.hue02_beautiful_whimsical: 0.9},
            ),
        ]
        with pytest.raises(ValidationError) as exc_info:
            PreferenceQuestionContent(
                question_text="Duplicate options:",
                answers=answers,
            )
        assert "unique" in str(exc_info.value).lower()

    def test_age_below_zero_rejected(self):
        """Age cannot be negative."""
        with pytest.raises(ValidationError) as exc_info:
            PreferenceQuestionContent(
                question_text="Test",
                min_age=-1,
                answers=[
                    PreferenceAnswer(text="A", hue_map={}),
                    PreferenceAnswer(text="B", hue_map={}),
                ],
            )
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_age_above_99_rejected(self):
        """Age cannot exceed 99."""
        with pytest.raises(ValidationError) as exc_info:
            PreferenceQuestionContent(
                question_text="Test",
                max_age=100,
                answers=[
                    PreferenceAnswer(text="A", hue_map={}),
                    PreferenceAnswer(text="B", hue_map={}),
                ],
            )
        assert "less than or equal to 99" in str(exc_info.value)

    def test_age_boundary_values(self):
        """Age boundaries 0 and 99 are valid."""
        answers = [
            PreferenceAnswer(text="A", hue_map={}),
            PreferenceAnswer(text="B", hue_map={}),
        ]
        question = PreferenceQuestionContent(
            question_text="All ages:",
            min_age=0,
            max_age=99,
            answers=answers,
        )
        assert question.min_age == 0
        assert question.max_age == 99


class TestPreferenceQuestionIntegration:
    """Integration tests for realistic preference question scenarios."""

    def test_realistic_huey_preference_question(self):
        """Test a realistic preference question with multiple hue mappings."""
        question = PreferenceQuestionContent(
            question_text="Which mystery door will you go through?",
            min_age=5,
            max_age=14,
            answers=[
                PreferenceAnswer(
                    text="The dark, creaky door with cobwebs",
                    image_url="https://storage.example.com/doors/dark.png",
                    hue_map={
                        HueKeys.hue01_dark_suspense: 1.0,
                        HueKeys.hue03_dark_beautiful: 0.8,
                        HueKeys.hue02_beautiful_whimsical: 0.1,
                    },
                ),
                PreferenceAnswer(
                    text="The bright door with flowers",
                    image_url="https://storage.example.com/doors/bright.png",
                    hue_map={
                        HueKeys.hue01_dark_suspense: 0.0,
                        HueKeys.hue02_beautiful_whimsical: 1.0,
                        HueKeys.hue04_joyful_charming: 0.7,
                    },
                ),
                PreferenceAnswer(
                    text="The mysterious glowing portal",
                    image_url="https://storage.example.com/doors/portal.png",
                    hue_map={
                        HueKeys.hue07_silly_charming: 0.3,
                        HueKeys.hue08_charming_courageous: 0.9,
                        HueKeys.hue01_dark_suspense: 0.4,
                    },
                ),
            ],
        )

        assert question.question_text == "Which mystery door will you go through?"
        assert question.min_age == 5
        assert question.max_age == 14
        assert len(question.answers) == 3

        # Verify first answer has expected hue values
        dark_door = question.answers[0]
        assert dark_door.hue_map[HueKeys.hue01_dark_suspense] == 1.0
        assert HueKeys.hue02_beautiful_whimsical in dark_door.hue_map

    def test_model_serialization_roundtrip(self):
        """Test that models can be serialized and deserialized."""
        original = PreferenceQuestionContent(
            question_text="Test question",
            min_age=8,
            max_age=12,
            answers=[
                PreferenceAnswer(
                    text="Answer 1",
                    hue_map={HueKeys.hue10_inspiring: 0.7},
                ),
                PreferenceAnswer(
                    text="Answer 2",
                    image_url="https://example.com/img.png",
                    hue_map={HueKeys.hue11_realistic_hope: 0.6},
                ),
            ],
        )

        # Serialize to dict
        data = original.model_dump()

        # Deserialize back
        restored = PreferenceQuestionContent.model_validate(data)

        assert restored.question_text == original.question_text
        assert restored.min_age == original.min_age
        assert len(restored.answers) == len(original.answers)
