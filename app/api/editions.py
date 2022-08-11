import math
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Security
from sqlalchemy import and_, func
from sqlalchemy.orm import Session
from structlog import get_logger

from app import crud
from app.api.common.pagination import PaginatedQueryParams
from app.api.dependencies.security import get_current_active_user_or_service_account
from app.db.session import get_session
from app.models import Edition
from app.models.collection_item import CollectionItem
from app.models.labelset import LabelSet
from app.models.work import Work
from app.schemas.edition import (
    EditionBrief,
    EditionCreateIn,
    EditionDetail,
    KnownAndTaggedEditionCounts,
)
from app.services.editions import (
    compare_known_editions,
    create_missing_editions,
    get_definitive_isbn,
)

logger = get_logger()
router = APIRouter(
    tags=["Books"], dependencies=[Security(get_current_active_user_or_service_account)]
)


@router.get("/editions", response_model=List[EditionBrief])
async def get_editions(
    work_id: Optional[str] = Query(None, description="Filter editions by work"),
    query: Optional[str] = Query(None, description="Query string"),
    pagination: PaginatedQueryParams = Depends(),
    session: Session = Depends(get_session),
):
    if work_id is not None:
        work = crud.work.get_or_404(session, id=work_id)
        return work.editions[pagination.skip : pagination.skip + pagination.limit]
    elif query is not None:
        statement = crud.edition.get_all_query(session).where(
            Edition.title.match(query)
        )
        return session.execute(statement).scalars().all()
    else:
        return crud.edition.get_all(
            session, skip=pagination.skip, limit=pagination.limit
        )


@router.post("/editions/compare", response_model=KnownAndTaggedEditionCounts)
async def compare_bulk_editions(
    isbn_list: List[str], session: Session = Depends(get_session)
):
    """
    Compares a list of ISBNs against the db to determine how many are valid,
    how many of those Huey knows about, and how many of those have been fully tagged and checked.
    The provided list should be a raw JSON list, i.e:

    ```json
    [
        "1234567890",
        "1234567899",
        "1234567898"
    ]
    ```

    """
    valid, known, fully_tagged = await compare_known_editions(session, isbn_list)

    return {
        "num_provided": len(isbn_list),
        "num_valid": valid,
        "num_known": known,
        "num_fully_tagged": fully_tagged,
    }


@router.get("/edition/{isbn}", response_model=EditionDetail)
async def get_book_by_isbn(isbn: str, session: Session = Depends(get_session)):
    try:
        isbn = get_definitive_isbn(isbn)
    except:
        raise HTTPException(422, "Invalid isbn")

    return crud.edition.get_or_404(db=session, id=isbn)


@router.post("/edition", response_model=EditionDetail)
async def add_edition(
    edition_data: EditionCreateIn, session: Session = Depends(get_session)
):
    return crud.edition.create_new_edition(session, edition_data)


@router.post("/editions")
async def bulk_add_editions(
    bulk_edition_data: List[EditionCreateIn], session: Session = Depends(get_session)
):
    isbns, created, existing = await create_missing_editions(
        session, new_edition_data=bulk_edition_data
    )

    return {
        "msg": f"Bulk load of {len(isbns)} editions complete. Created {created} new editions."
    }


@router.get("/editions/to_hydrate", response_model=List[EditionBrief])
async def get_editions(
    pagination: PaginatedQueryParams = Depends(),
    session: Session = Depends(get_session),
):

    # ----manual override to prioritise certain schools 07/07/22----

    priority_ids = [
        5082,  # marist
        10274,  # willyama
        4534,  # kurunjang
        4001,  # international grammar
        727,  # beauty point
        10750,  # st gabriels
        132,  # all hallows
        9495,  # scots pgc
        316,  # ascham
    ]

    priority_queries = [
        session.query(Edition)
        .join(CollectionItem)
        .join(Work, isouter=True)
        .join(LabelSet, isouter=True)
        .where(LabelSet.min_age == None)
        .where(
            and_(
                (CollectionItem.school_id == priority_id),
                (Edition.hydrated == False),
            )
        )
        .order_by(func.random())
        .limit(math.ceil(pagination.limit / 10) if pagination.limit else 500)
        for priority_id in priority_ids
    ]

    allschool_query = (
        session.query(Edition, Edition.num_schools)
        .join(Work, isouter=True)
        .join(LabelSet, isouter=True)
        .order_by(Edition.num_schools.desc())
        .where(Edition.hydrated == False)
        .where(LabelSet.min_age == None)
        .limit(math.ceil(pagination.limit / 10) if pagination.limit else 500)
    )

    # query = session.query(allschool_subquery, *priority_subqueries)

    results = [
        session.execute(q).scalars().all() for q in priority_queries + [allschool_query]
    ]
    return [edition for result in results for edition in result]  # 🥴

    # q = (
    #     session.query(Edition, Edition.num_schools)
    #     .order_by(Edition.num_schools.desc())
    #     .where(Edition.hydrated == False)
    #     .limit(pagination.limit if pagination.limit else 5000)
    # )

    # return session.execute(q).scalars().all()
