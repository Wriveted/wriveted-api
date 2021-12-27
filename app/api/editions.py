from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from structlog import get_logger

from app import crud
from app.api.common.pagination import PaginatedQueryParams
from app.db.session import get_session
from app.models import Edition
from app.models.work import WorkType
from app.schemas.edition import EditionDetail, EditionBrief, EditionCreateIn
from app.schemas.work import WorkCreateIn

logger = get_logger()
router = APIRouter(
    tags=["Books"]
)


@router.get("/editions", response_model=List[EditionBrief])
async def get_editions(pagination: PaginatedQueryParams = Depends(), session: Session = Depends(get_session)):
    return crud.edition.get_all(session, skip=pagination.skip, limit=pagination.limit)


@router.get("/edition/{isbn}", response_model=EditionDetail)
async def get_book_by_isbn(isbn: str, session: Session = Depends(get_session)):
    return crud.edition.get_or_404(db=session, id=isbn)


@router.post("/edition", response_model=EditionDetail)
async def add_edition(
        edition_data: EditionCreateIn,
        session: Session = Depends(get_session)
):
    return create_new_edition(session, edition_data)


@router.post("/editions")
async def bulk_add_editions(
        bulk_edition_data: List[EditionCreateIn],
        session: Session = Depends(get_session)
):
    # TODO ideally this should use a bulk api
    # Need to account for new authors, works, and series created
    # in a single upload and referenced multiple times though...

    editions = [
        create_new_edition(session, edition_data, commit=True)
        for edition_data in bulk_edition_data
    ]
    #session.commit()
    return {
        "msg": f"Bulk load of {len(editions)} editions complete"
    }


def create_new_edition(session, edition_data, commit=True):
    # Get or create the authors
    authors = [
        crud.author.get_or_create(session, author_data, commit=False)
        for author_data in edition_data.authors
    ]
    # Get or create the work
    work_create_data = WorkCreateIn(
        type=WorkType.BOOK,
        title=edition_data.work_title if edition_data.work_title is not None else edition_data.title,
        authors=edition_data.authors,
        info=edition_data.info,
        series_title=edition_data.series_title,
    )
    work = crud.work.get_or_create(
        session,
        work_data=work_create_data,
        authors=authors,
        commit=False
    )
    # Get or create the illustrators
    illustrators = [
        crud.illustrator.get_or_create(
            session,
            illustrator_data,
            commit=False
        )
        for illustrator_data in edition_data.illustrators
    ]
    # Then, at last create the edition - raising an error if it already existed
    edition = crud.edition.create(
        db=session,
        edition_data=edition_data,
        work=work,
        illustrators=illustrators,
        commit=commit
    )
    return edition