"""
Chatbot-specific API integrations for Wriveted platform services.

These endpoints provide simplified, chatbot-optimized interfaces to existing
Wriveted services like recommendations, user profiles, and reading assessments.

In Landbot days this was part of the flow.
"""

from typing import Any, Dict, List, Optional, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import distinct, func, select
from structlog import get_logger

from app import crud
from app.api.dependencies.async_db_dep import DBSessionDep
from app.api.dependencies.security import get_current_active_user_or_service_account
from app.models import CollectionItem, Edition, Hue, LabelSet, Student, Work
from app.models.collection_item_activity import (
    CollectionItemActivity,
    CollectionItemReadStatus,
)
from app.models.labelset_hue_association import LabelSetHue
from app.repositories.school_repository import school_repository

# from app.schemas.recommendations import ReadingAbilityKey  # Future use for reading level mapping
from app.services.recommendations import get_recommended_labelset_query

logger = get_logger()

router = APIRouter(
    prefix="/chatbot",
    tags=["Chatbot Integrations"],
    dependencies=[Depends(get_current_active_user_or_service_account)],
)


# Request/Response Models for Chatbot API


class ChatbotRecommendationRequest(BaseModel):
    """Request for chatbot book recommendations."""

    user_id: UUID
    preferences: Dict[str, Any] = Field(default_factory=dict)
    limit: int = Field(default=5, ge=1, le=20)
    exclude_isbns: List[str] = Field(default_factory=list)

    # Optional overrides
    reading_level: Optional[str] = None
    age: Optional[int] = None
    genres: List[str] = Field(default_factory=list)
    hues: List[str] = Field(default_factory=list)


class ChatbotRecommendationResponse(BaseModel):
    """Response for chatbot book recommendations."""

    recommendations: List[Dict[str, Any]]
    count: int
    user_reading_level: Optional[str] = None
    filters_applied: Dict[str, Any]
    fallback_used: bool = False


class ReadingAssessmentRequest(BaseModel):
    """Request for reading level assessment."""

    user_id: UUID
    assessment_data: Dict[str, Any]

    # Assessment types
    quiz_answers: Optional[Dict[str, Any]] = None
    reading_sample: Optional[str] = None
    comprehension_score: Optional[float] = None
    vocabulary_score: Optional[float] = None

    # Context
    current_reading_level: Optional[str] = None
    age: Optional[int] = None


class ReadingAssessmentResponse(BaseModel):
    """Response for reading assessment."""

    reading_level: str
    confidence: float = Field(ge=0.0, le=1.0)
    level_description: str
    recommendations: List[str] = Field(default_factory=list)

    # Assessment details
    assessment_summary: Dict[str, Any]
    next_steps: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    areas_for_improvement: List[str] = Field(default_factory=list)


class UserProfileResponse(BaseModel):
    """Response for user profile data."""

    user_id: UUID
    reading_level: Optional[str] = None
    interests: List[str] = Field(default_factory=list)
    reading_history: List[Dict[str, Any]] = Field(default_factory=list)

    # School context
    school_name: Optional[str] = None
    school_id: Optional[UUID] = None
    class_group: Optional[str] = None

    # Reading stats
    books_read_count: int = 0
    average_reading_time: Optional[float] = None
    favorite_genres: List[str] = Field(default_factory=list)


# API Endpoints


@router.post("/recommendations", response_model=ChatbotRecommendationResponse)
async def get_chatbot_recommendations(
    request: ChatbotRecommendationRequest,
    db: DBSessionDep,
    account=Depends(get_current_active_user_or_service_account),
) -> ChatbotRecommendationResponse:
    """
    Get book recommendations optimized for chatbot conversations.

    This endpoint provides a simplified interface to the recommendation engine
    with chatbot-specific response formatting and fallback handling.
    """
    try:
        # Get user for context
        user = await crud.user.aget_or_404(db=db, id=request.user_id)

        # Extract user information
        user_age = None
        user_reading_level = None
        school_id = None

        if isinstance(user, Student):
            user_age = user.age
            user_reading_level = getattr(user, "reading_level", None)
            school_id = user.school_id

        # Apply overrides from request
        final_age = request.age or user_age
        final_reading_level = request.reading_level or user_reading_level

        # Reading level to reading abilities mapping
        reading_abilities = []
        if final_reading_level:
            try:
                reading_abilities = [final_reading_level]
                # Also include adjacent levels for variety (future enhancement)
                # This would use the gen_next_reading_ability function
            except (ValueError, KeyError):
                logger.warning(f"Invalid reading level: {final_reading_level}")

        # Use hues from request or map from genres
        hues = (
            request.hues or request.genres if request.hues or request.genres else None
        )

        # Get recommendations using existing service
        query = await get_recommended_labelset_query(
            asession=db,
            hues=hues,
            collection_id=school_id,
            age=final_age,
            reading_abilities=reading_abilities if reading_abilities else None,
            recommendable_only=True,
            exclude_isbns=request.exclude_isbns if request.exclude_isbns else None,
        )

        # Execute query with limit
        result = await db.execute(query.limit(request.limit))
        recommendations_data = result.all()

        # Format recommendations for chatbot
        recommendations = []
        for work, edition, labelset in recommendations_data:
            rec = {
                "id": str(work.id),
                "title": work.title,
                "author": work.primary_author_name
                if hasattr(work, "primary_author_name")
                else "Unknown",
                "isbn": edition.isbn,
                "cover_url": edition.cover_url,
                "reading_level": labelset.reading_level
                if hasattr(labelset, "reading_level")
                else None,
                "description": work.description
                if hasattr(work, "description")
                else None,
                "age_range": {
                    "min": labelset.min_age if hasattr(labelset, "min_age") else None,
                    "max": labelset.max_age if hasattr(labelset, "max_age") else None,
                },
                "genres": [],  # Would extract from hues/labels
                "recommendation_score": 0.85,  # Placeholder for ML scoring
            }
            recommendations.append(rec)

        filters_applied = {
            "reading_level": final_reading_level,
            "age": final_age,
            "hues": hues,
            "exclude_isbns": request.exclude_isbns,
            "limit": request.limit,
        }

        return ChatbotRecommendationResponse(
            recommendations=recommendations,
            count=len(recommendations),
            user_reading_level=final_reading_level,
            filters_applied=filters_applied,
            fallback_used=False,
        )

    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")

        # Return fallback response
        return ChatbotRecommendationResponse(
            recommendations=[],
            count=0,
            user_reading_level=request.reading_level,
            filters_applied={},
            fallback_used=True,
        )


@router.post("/assessment/reading-level", response_model=ReadingAssessmentResponse)
async def assess_reading_level(
    request: ReadingAssessmentRequest,
    db: DBSessionDep,
    account=Depends(get_current_active_user_or_service_account),
) -> ReadingAssessmentResponse:
    """
    Assess user's reading level based on quiz responses and reading samples.

    This endpoint provides reading level assessment with detailed feedback
    suitable for chatbot conversations.
    """
    try:
        # Get user for context
        user = await crud.user.aget_or_404(db=db, id=request.user_id)

        # Extract current context
        current_level = request.current_reading_level
        user_age = request.age

        if isinstance(user, Student) and not user_age:
            user_age = user.age

        # Analyze assessment data
        assessment_score = 0.0
        confidence = 0.0

        # Quiz analysis
        if request.quiz_answers is not None:
            quiz_score = _analyze_quiz_responses(
                cast(Dict[str, Any], request.quiz_answers)
            )
            assessment_score += quiz_score * 0.4
            confidence += 0.3

        # Reading comprehension analysis
        if request.comprehension_score is not None:
            assessment_score += float(request.comprehension_score) * 0.4
            confidence += 0.4

        # Vocabulary analysis
        if request.vocabulary_score is not None:
            assessment_score += float(request.vocabulary_score) * 0.2
            confidence += 0.3

        # Reading sample analysis (simplified)
        if request.reading_sample is not None:
            sample_score = _analyze_reading_sample(cast(str, request.reading_sample))
            assessment_score += sample_score * 0.3
            confidence += 0.2

        # Normalize confidence
        confidence = min(1.0, confidence)

        # Determine reading level based on score and age
        new_reading_level = _determine_reading_level(
            assessment_score, user_age, current_level
        )

        # Generate assessment feedback
        level_description = _get_level_description(new_reading_level)
        recommendations = _get_level_recommendations(new_reading_level)
        strengths, improvements = _analyze_performance(request.assessment_data)

        # Create assessment summary
        assessment_summary = {
            "overall_score": round(assessment_score, 2),
            "confidence": round(confidence, 2),
            "assessment_type": "comprehensive",
            "components_analyzed": [
                comp
                for comp in ["quiz", "comprehension", "vocabulary", "sample"]
                if getattr(
                    request,
                    f"{comp}_score" if comp != "quiz" else f"{comp}_answers",
                    None,
                )
                is not None
            ],
            "age_considered": user_age,
            "previous_level": current_level,
            "level_change": current_level != new_reading_level
            if current_level
            else "initial_assessment",
        }

        # Update user reading level if confidence is high enough
        if confidence > 0.7 and isinstance(user, Student):
            # This would update the user's reading level in the database
            # await crud.user.update_reading_level(db, user.id, new_reading_level)
            pass

        return ReadingAssessmentResponse(
            reading_level=new_reading_level,
            confidence=confidence,
            level_description=level_description,
            recommendations=recommendations,
            assessment_summary=assessment_summary,
            next_steps=_get_next_steps(new_reading_level, assessment_score),
            strengths=strengths,
            areas_for_improvement=improvements,
        )

    except Exception as e:
        logger.error(f"Error in reading assessment: {e}")
        raise HTTPException(status_code=500, detail="Assessment failed")


@router.get("/users/{user_id}/profile", response_model=UserProfileResponse)
async def get_user_profile(
    user_id: UUID,
    db: DBSessionDep,
    account=Depends(get_current_active_user_or_service_account),
) -> UserProfileResponse:
    """
    Get comprehensive user profile data for chatbot context.

    Returns user reading profile, school context, and reading statistics
    formatted for chatbot conversations.
    """
    try:
        # Get user with related data
        user = await crud.user.aget_or_404(db=db, id=user_id)

        # Build profile response
        profile = UserProfileResponse(user_id=user_id)

        if isinstance(user, Student):
            profile.reading_level = getattr(user, "reading_level", None)

            # Get school context
            if user.school_id:
                try:
                    school = await school_repository.aget(db=db, id=user.school_id)
                    if school:
                        profile.school_name = school.name
                        profile.school_id = school.id
                except Exception:
                    pass

            # Get class group if available
            if hasattr(user, "class_group"):
                profile.class_group = (
                    getattr(user.class_group, "name", None)
                    if user.class_group
                    else None
                )

        # Get reading statistics.
        # Populate books_read_count
        books_read_count_query = select(
            func.count(distinct(CollectionItemActivity.collection_item_id))
        ).where(
            CollectionItemActivity.reader_id == user_id,
            CollectionItemActivity.status == CollectionItemReadStatus.READ,
        )
        profile.books_read_count = (await db.scalar(books_read_count_query)) or 0

        # Populate reading_history
        reading_history_query = (
            select(
                Work.title,
                Work.primary_author_name,
                Edition.isbn,
                Edition.cover_url,
                CollectionItemActivity.timestamp,
            )
            .join(
                CollectionItem,
                CollectionItemActivity.collection_item_id == CollectionItem.id,
            )
            .join(Edition, CollectionItem.edition_id == Edition.id)
            .join(Work, Edition.work_id == Work.id)
            .where(CollectionItemActivity.reader_id == user_id)
            .order_by(CollectionItemActivity.timestamp.desc())
            .limit(10)  # Limit to 10 most recent books
        )
        recent_activities = (await db.execute(reading_history_query)).all()

        profile.reading_history = []
        for title, author, isbn, cover_url, timestamp in recent_activities:
            profile.reading_history.append(
                {
                    "title": title,
                    "author": author,
                    "isbn": isbn,
                    "cover_url": cover_url,
                    "last_activity_at": timestamp.isoformat(),
                }
            )

        # Populate favorite_genres and interests
        favorite_genres_query = (
            select(Hue.name, func.count(Hue.name).label("genre_count"))
            .join(LabelSetHue, Hue.id == LabelSetHue.hue_id)
            .join(LabelSet, LabelSetHue.labelset_id == LabelSet.id)
            .join(Work, LabelSet.work_id == Work.id)
            .join(Edition, Work.id == Edition.work_id)
            .join(CollectionItem, Edition.id == CollectionItem.edition_id)
            .join(
                CollectionItemActivity,
                CollectionItem.id == CollectionItemActivity.collection_item_id,
            )
            .where(
                CollectionItemActivity.reader_id == user_id,
                CollectionItemActivity.status == CollectionItemReadStatus.READ,
            )
            .group_by(Hue.name)
            .order_by(func.count(Hue.name).desc())
            .limit(5)
        )
        favorite_genres_results = (await db.execute(favorite_genres_query)).all()
        profile.favorite_genres = [genre for genre, count in favorite_genres_results]
        profile.interests = (
            profile.favorite_genres
        )  # For now, interests are derived from favorite genres

        return profile

    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        raise HTTPException(status_code=500, detail="Profile retrieval failed")


# Helper functions for assessment logic


def _analyze_quiz_responses(quiz_answers: Dict[str, Any]) -> float:
    """Analyze quiz responses and return score 0-1."""
    correct_answers = quiz_answers.get("correct", 0)
    total_questions = quiz_answers.get("total", 1)
    return correct_answers / total_questions if total_questions > 0 else 0.0


def _analyze_reading_sample(reading_sample: str) -> float:
    """Analyze reading sample and return complexity score 0-1."""
    # Simplified analysis - would use NLP in production
    word_count = len(reading_sample.split())
    sentence_count = (
        reading_sample.count(".")
        + reading_sample.count("!")
        + reading_sample.count("?")
    )

    if sentence_count == 0:
        return 0.5

    avg_words_per_sentence = word_count / sentence_count

    # Simple heuristic
    if avg_words_per_sentence < 8:
        return 0.3
    elif avg_words_per_sentence < 15:
        return 0.6
    else:
        return 0.9


def _determine_reading_level(
    score: float, age: Optional[int], current_level: Optional[str]
) -> str:
    """Determine reading level based on assessment score and age."""
    # Simplified mapping - would use more sophisticated logic
    level_mapping = {
        (0.0, 0.3): "early_reader",
        (0.3, 0.5): "developing_reader",
        (0.5, 0.7): "intermediate",
        (0.7, 0.85): "advanced",
        (0.85, 1.0): "expert",
    }

    for (min_score, max_score), level in level_mapping.items():
        if min_score <= score < max_score:
            return level

    return "intermediate"  # Default


def _get_level_description(reading_level: str) -> str:
    """Get description for reading level."""
    descriptions = {
        "early_reader": "You're just starting your reading journey! You can read simple sentences and short books.",
        "developing_reader": "You're building great reading skills! You can read chapter books and understand stories well.",
        "intermediate": "You're a confident reader! You can enjoy longer books and understand complex stories.",
        "advanced": "You're an excellent reader! You can tackle challenging books and analyze deeper meanings.",
        "expert": "You're a reading expert! You can handle any book and think critically about complex texts.",
    }
    return descriptions.get(reading_level, "You're developing your reading skills!")


def _get_level_recommendations(reading_level: str) -> List[str]:
    """Get recommendations for reading level."""
    recommendations = {
        "early_reader": [
            "Try picture books with simple sentences",
            "Read aloud with a grown-up",
            "Look for books with repetitive patterns",
        ],
        "developing_reader": [
            "Explore chapter books with illustrations",
            "Try series books with familiar characters",
            "Read books about topics you love",
        ],
        "intermediate": [
            "Challenge yourself with longer novels",
            "Try different genres like mystery or fantasy",
            "Join a book club or reading group",
        ],
        "advanced": [
            "Explore classic literature",
            "Read books that make you think deeply",
            "Try writing book reviews or discussions",
        ],
        "expert": [
            "Read across all genres and time periods",
            "Analyze themes and literary techniques",
            "Mentor younger readers",
        ],
    }
    return recommendations.get(reading_level, ["Keep reading and exploring new books!"])


def _analyze_performance(
    assessment_data: Dict[str, Any],
) -> tuple[List[str], List[str]]:
    """Analyze performance and return strengths and improvement areas."""
    # Simplified analysis
    strengths = ["Reading comprehension", "Vocabulary recognition"]
    improvements = ["Reading speed", "Critical thinking"]
    return strengths, improvements


def _get_next_steps(reading_level: str, score: float) -> List[str]:
    """Get next steps for reading development."""
    next_steps = [
        f"Continue reading at the {reading_level} level",
        "Try books slightly above your current level for growth",
        "Keep a reading journal to track your progress",
    ]

    if score < 0.6:
        next_steps.append("Practice reading aloud to build fluency")
        next_steps.append("Ask questions about what you read")

    return next_steps
