from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.orm import Session
from app import crud
from app.api.common.pagination import PaginatedQueryParams
from app.api.dependencies.security import get_current_active_user_or_service_account
from app.db.session import get_session
from app.models.collection_item import CollectionItem
from app.models.edition import Edition
from app.models.hue import Hue
from app.models.labelset import LabelSet
from app.models.reading_ability import ReadingAbility
from app.models.school import School
from app.models.work import Work
from app.schemas.work import WorkBrief, WorkDetail

router = APIRouter(
    # tags=["Books"], dependencies=[Depends(get_current_active_user_or_service_account)]
)

class HueyBook(BaseModel):
    cover_url: str
    display_title: str # {leading article} {title} (leading article is optional, thus bridging whitespace optional)
    authors_string: str # {a1.first_name} {a1.last_name}, {a2.first_name} {a2.last_name} ... (first name is optional, thus bridging whitespace optional)
    summary: str

class HueyOutput(BaseModel):
    count: int
    books: list[HueyBook]

@router.get("/works", response_model=HueyOutput)
async def get_works(
    school_id: int = Query(None),
    age: int = Query(None),
    reading_ability: str = Query(None),
    hues: list[str] = Query(None),
    # pagination: PaginatedQueryParams = Depends(),
    session: Session = Depends(get_session),
):
    """A multiple-parameter query intended for fetching book data for Huey chats.
    Should probably have its own endpoint since it doesn't really belong to a single tabular concept"""

    # select collection_item as ci where ci.school_id = school_id 
    # and ci.edition.work.labelset.min_age >= age
    # and ci.edition.work.labelset.max_age <= age
    # any reading ability match
    # any hue match

    # stmt = session.query(CollectionItem, Edition, Work, LabelSet, Hue, ReadingAbility) \
    #     .select_from(CollectionItem).join(Edition).join(Work).join(LabelSet).join(LabelSet.hues).join(LabelSet.reading_abilities) \
    #     .filter(
    #         and_(
    #             CollectionItem.school_id == school_id,
    #             # LabelSet.checked,
    #             LabelSet.min_age <= age,
    #             LabelSet.max_age >= age,
    #             # LabelSet.hues.any(Hue.key in hues),
    #             # LabelSet.reading_abilities.any(ReadingAbility.key == reading_ability),
    #             # LabelSet.huey_summary IS NOT NULL
    #         )
    #     ) \
    #     .limit(5)

    # result = session.execute(stmt.where(LabelSet.hues.any(Hue.key in hues)))
    # print(result)


    # fallback logic can come later when booklists are implented

    # fallback_q = select(Edition).where(
    #     and_(
    #         Edition.work.booklists.any(BookList.key == "wriveted_huey_picks"),
    #         Edition.work.labelset.min_age <= age,
    #         Edition.work.labelset.max_age >= age,
    #         Edition.work.labelset.reading_abilities.key == reading_ability,
    #         Edition.work.labelset.hues.any(Hue.key.in_(hues))
    #     ) \
    #     .limit(5)
    # )

    # editions: list[Edition] = session.execute(main_q).scalars().all()
    
    # return [{"cover_url": e.cover_url, "display_title": e.title, "authors_string": e.get_authors_string(), "summary": e.work.labelset.huey_summary} for e in editions]

    return {
        "count":5, 
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


@router.get("/work/{work_id}", response_model=WorkDetail)
async def get_work_by_id(work_id: str, session: Session = Depends(get_session)):
    return crud.work.get_or_404(db=session, id=work_id)
