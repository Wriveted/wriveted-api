import enum
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from structlog import get_logger


from app.api.dependencies.security import get_current_active_user_or_service_account
from app.db.session import get_session
from app.schemas.recommendations import HueyBook, HueyOutput

from app.services.recommendations import get_recommended_labelset_query

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

    labelsets = session.execute(labelset_query.limit(5)).scalars().all()
    logger.info(f"Recommending {len(labelsets)}", recommendations=labelsets)

    # fallback logic can come later when booklists are implemented

    return {
        "count": 5,
        "books":[
            HueyBook(
                cover_url="https://storage.googleapis.com/wriveted-cover-images/nielsen/9781408314807.jpg",
                display_title="Beware of The Storybook Wolves",
                authors_string="Lauren Child",
                summary="For a real thrill, try reading Beware of the Storybook Wolves. It will scare your socks off!" +
                        " A fun-filled picture book with a fairytale twist, from Children's Laureate, and Charlie & Lola creator, Lauren Child."
            ),
            HueyBook(
                cover_url="https://storage.googleapis.com/wriveted-cover-images/nielsen/9781408314807.jpg",
                display_title="Bewa2re of The2 Story2book Wolves222",
                authors_string="Laur2en Ch2i2ld",
                summary="For a real 2thrill, try r2eading Beware of the Storybook Wol2ves. It will 2scare your socks off!" +
                        " A fun-filled picture book with a fairytale twi2st, from Child2ren's Laureate, and Charl2ie & Lola creator, Lauren Child."
            ),
            HueyBook(
                cover_url="https://storage.googleapis.com/wriveted-cover-images/nielsen/9781408314807.jpg",
                display_title="Beware 3of The Storybook Wolves333",
                authors_string="Laur3en Child",
                summary="For a re3al thrill, try reading Bewa3re of the Storybook Wolves. It w3ill scare y3our socks off!" +
                        " A fun-filled 3picture book with a fa3irytale twist, from Children's L3aureate, and 3Charlie & Lola creator, Lauren Child."
            ),
            HueyBook(
                cover_url="https://storage.googleapis.com/wriveted-cover-images/nielsen/9781408314807.jpg",
                display_title="Bew44are 4of The St4orybook W4ol4ves",
                authors_string="Laure4n Child",
                summary="For a real 4thrill, try reading Beware4 of the 4Storybook Wolves. It will scare your socks off!" +
                        " A fun-fille4d picture book w4ith a fairytale twist, from Ch4ildren's Laure4ate, and 4Charlie & Lola creator, Lauren Child."
            ),
            HueyBook(
                cover_url="https://storage.googleapis.com/wriveted-cover-images/nielsen/9781408314807.jpg",
                display_title="Bewar5e of The 5Storybook Wolves",
                authors_string="5Laur5en 5Child",
                summary="For a real t5hrill, try reading B5eware of the Storybook Wo5lves555. It will scare your socks55 off!" +
                        " A fun-filled p55icture book5 with a5 fairytale twist,5 from Chi5ldren's Laureate, and Charlie5 & 5Lola creator, Lauren Child."
            ),
        ]
    }
