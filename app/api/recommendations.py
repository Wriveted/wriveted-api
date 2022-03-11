import enum
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session
from structlog import get_logger

from app import crud

from app.api.dependencies.security import get_current_active_user_or_service_account
from app.db.session import get_session

from app.schemas.recommendations import HueyBook, HueyOutput
from app.services.events import create_event

from app.services.recommendations import get_any_edition_and_labelset_query, get_recommended_labelset_query, \
    get_school_specific_edition_and_labelset_query

router = APIRouter(
    tags=["Recommendations"],
    dependencies=[Depends(get_current_active_user_or_service_account)]
)
logger = get_logger()


class ReadingAbilityKey(str, enum.Enum):
    SPOT = 'SPOT'
    CAT_HAT = 'CAT_HAT'
    TREEHOUSE = 'TREEHOUSE'
    CHARLIE_CHOCOLATE = 'CHARLIE_CHOCOLATE'
    HARRY_POTTER = 'HARRY_POTTER'


class HueKeys(str, enum.Enum):
    hue01_dark_suspense = 'hue01_dark_suspense'
    hue02_beautiful_whimsical = 'hue02_beautiful_whimsical'
    hue03_dark_beautiful = 'hue03_dark_beautiful'
    hue05_funny_comic = 'hue05_funny_comic'
    hue06_dark_gritty = 'hue06_dark_gritty'
    hue07_silly_charming = 'hue07_silly_charming'
    hue08_charming_inspiring = 'hue08_charming_inspiring'
    hue09_charming_playful = 'hue09_charming_playful'
    hue10_inspiring = 'hue10_inspiring'
    hue11_realistic_hope = 'hue11_realistic_hope'
    hue12_funny_quirky = 'hue12_funny_quirky'
    hue13_straightforward = 'hue13_straightforward'


# @router.get("/recommendations", response_model=HueyOutput)
# async def get_recommendations(
#         hues: list[HueKeys] = Query(None),
#         school: Optional[School] = Depends(get_optional_school_from_wriveted_id_query),
#         #school: Optional[School] = Permission("read", get_optional_school_from_wriveted_id_query),
#         age: Optional[int] = Query(None),
#         reading_ability: Optional[ReadingAbilityKey] = Query(None),
#
#         # pagination: PaginatedQueryParams = Depends(),
#         account=Depends(get_current_active_user_or_service_account),
#         session: Session = Depends(get_session),
# ):
#     """
#     Fetch labeled works as recommended by Huey.
#
#     Note this endpoint is limited to returning 5 recommendations at a time.
#     """
#     row_results = await get_recommendations_with_fallback(session, account, hues, reading_ability, school, age)
#     return {
#         "count": len(row_results),
#         "books":[
#             HueyBook(
#                 cover_url=edition.cover_url,
#                 display_title=edition.title,
#                 authors_string=', '.join(str(a) for a in labelset.work.authors),
#                 summary=labelset.huey_summary
#             ) for (edition, labelset) in row_results
#         ]
#     }


class HueyRecommendationFilter(BaseModel):
    hues: list[HueKeys] = None
    age: Optional[int] = None
    reading_ability: Optional[ReadingAbilityKey] = None
    wriveted_identifier: Optional[uuid.UUID] = None


@router.post("/recommend", response_model=HueyOutput)
async def get_recommendations(
        data: HueyRecommendationFilter,
        background_tasks: BackgroundTasks,
        # pagination: PaginatedQueryParams = Depends(),
        account=Depends(get_current_active_user_or_service_account),
        session: Session = Depends(get_session),

):
    """
    Fetch labeled works as recommended by Huey.

    Note this endpoint is limited to returning 5 recommendations at a time.
    """
    hues = data.hues
    age = data.age
    reading_ability = data.reading_ability

    if data.wriveted_identifier is not None:
        school = crud.school.get_by_wriveted_id_or_404(
            db=session, wriveted_id=data.wriveted_identifier
        )
        # TODO check account is allowed to `read` school
    else:
        school = None

    row_results = await get_recommendations_with_fallback(session, account, hues, reading_ability, school, age, background_tasks=background_tasks)
    return {
        "count": len(row_results),
        "books":[
            HueyBook(
                isbn=edition.isbn,
                cover_url=edition.cover_url,
                display_title=edition.title,
                authors_string=', '.join(str(a) for a in edition.work.authors),
                summary=labelset.huey_summary
            ) for (edition, labelset) in row_results
        ]
    }


async def get_recommendations_with_fallback(session, account, hues, reading_ability, school, age, background_tasks: BackgroundTasks):
    school_id = school.id if school is not None else None
    row_results = get_recommended_editions_and_labelsets(session, school_id, hues, reading_ability, age)

    if len(row_results) == 0:

        # proper fallback logic can come later when booklists are implemented
        # For now lets just strip the optional reading ability and try again
        row_results = get_recommended_editions_and_labelsets(session, school_id=school_id, hues=hues,
                                                             reading_ability=None, age=age)

        if len(row_results) == 0:
            # Still nothing... alright let's recommend outside the school collection
            row_results = get_recommended_editions_and_labelsets(session, school_id=None, hues=hues,
                                                                 reading_ability=None, age=age)

    if len(row_results) > 1:
        background_tasks.add_task(
            create_event,
            session,
            title=f"Made a recommendation of {len(row_results)} books",
            description=f"Recommended {', '.join(str(b[0].title) for b in row_results)}",
            school=school,
            account=account
        )
    else:
        if len(row_results) == 0:
            background_tasks.add_task(
                create_event,
                session,
                title="No books",
                description="No books met the criteria for recommendation",
                school=school,
                account=account
            )
    return row_results


def get_recommended_editions_and_labelsets(session, school_id, hues, reading_ability, age):
    labelset_query = get_recommended_labelset_query(
        session,
        hues=hues,
        school_id=school_id,
        age=age,
        reading_ability=reading_ability
    )
    if school_id is not None:
        edition_labelset_query = get_school_specific_edition_and_labelset_query(school_id, labelset_query)
    else:
        edition_labelset_query = get_any_edition_and_labelset_query(labelset_query)

    query = edition_labelset_query.limit(5).order_by(func.random())

    row_results = session.execute(query).all()
    return row_results
