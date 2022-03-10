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

class HueyOutput(BaseModel):
    cover_url: str
    display_title: str
    authors_string: str
    summary: str

@router.get("/works", response_model=List[HueyOutput])
async def get_works(
    school_id: int = Query(None),
    age: int = Query(None),
    reading_ability: str = Query(None),
    hues: list[str] = Query(None),
    # pagination: PaginatedQueryParams = Depends(),
    session: Session = Depends(get_session),
):

    stmt = session.query(CollectionItem, Edition, Work, LabelSet, Hue, ReadingAbility) \
        .select_from(CollectionItem).join(Edition).join(Work).join(LabelSet).join(LabelSet.hues).join(LabelSet.reading_abilities) \
        .filter(
            and_(
                CollectionItem.school_id == school_id,
                LabelSet.checked,
                LabelSet.min_age <= age,
                LabelSet.max_age >= age,
                # LabelSet.hues.any(Hue.key in hues),
                # LabelSet.reading_abilities.any(ReadingAbility.key == reading_ability)
            )
        )

    result = session.execute(stmt.where(LabelSet.hues.any(Hue.key in hues)))
    print(result)


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


@router.get("/work/{work_id}", response_model=WorkDetail)
async def get_work_by_id(work_id: str, session: Session = Depends(get_session)):
    return crud.work.get_or_404(db=session, id=work_id)
