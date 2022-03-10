import enum
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from structlog import get_logger


from app.api.dependencies.security import get_current_active_user_or_service_account
from app.db.session import get_session
from app.schemas.recommendations import HueyBook, HueyOutput

from app.services.recommendations import get_recommended_labelset_query, get_school_specific_edition_and_labelset_query

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


@router.get("/recommendations", response_model=HueyOutput)
async def get_recommendations(
        hues: list[HueKeys] = Query(None),
        school_id: Optional[int] = Query(None),
        age: Optional[int] = Query(None),
        reading_ability: Optional[ReadingAbilityKey] = Query(None),

        # pagination: PaginatedQueryParams = Depends(),
        session: Session = Depends(get_session),
):
    """
    Fetch labeled works as recommended by Huey.
    """
    labelset_query = get_recommended_labelset_query(
        session,
        hues=hues,
        school_id=school_id,
        age=age,
        reading_ability=reading_ability
    )

    edition_labelset_query = get_school_specific_edition_and_labelset_query(school_id, labelset_query)
    row_results = session.execute(edition_labelset_query.limit(5)).all()
    logger.info(f"Recommending {len(row_results)} books")

    # fallback logic can come later when booklists are implemented

    return {
        "count": len(row_results),
        "books":[
            HueyBook(
                cover_url=edition.cover_url,
                display_title=edition.title,
                authors_string=', '.join(str(a) for a in labelset.work.authors),
                summary=labelset.huey_summary
            ) for (edition, labelset) in row_results
        ]
    }
