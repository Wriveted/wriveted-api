from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Security
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette import status
from structlog import get_logger

from app import crud
from app.api.common.pagination import PaginatedQueryParams
from app.api.dependencies.editions import get_edition_from_isbn
from app.api.dependencies.security import get_current_active_user_or_service_account
from app.db.session import get_session
from app.models import Edition
from app.schemas import is_url
from app.schemas.edition import (
    EditionBrief,
    EditionCreateIn,
    EditionDetail,
    EditionUpdateIn,
    KnownAndTaggedEditionCounts,
)
from app.schemas.illustrator import IllustratorCreateIn
from app.services.cover_images import handle_edition_cover_image_update
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
        return session.scalars(statement).all()
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
    except AssertionError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid isbn")

    return crud.edition.get_or_404(db=session, id=isbn)


@router.post("/edition", response_model=EditionDetail)
async def add_edition(
    edition_data: EditionCreateIn,
    session: Session = Depends(get_session),
):
    try:
        edition = crud.edition.create_new_edition(session, edition_data)
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))

    if edition:
        return edition
    else:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Edition already exists with ISBN {edition_data.isbn}. Use the PATCH method to update.",
        )


@router.patch("/edition/{isbn}", response_model=EditionDetail)
async def update_edition(
    edition_data: EditionUpdateIn,
    session: Session = Depends(get_session),
    edition=Depends(get_edition_from_isbn),
    merge_dicts: bool = Query(
        default=False,
        description="Whether or not to *merge* the data in info dict, i.e. if adding new or updating existing individual fields (but want to keep previous data)",
    ),
    account=Depends(get_current_active_user_or_service_account),
):
    update_data = edition_data.dict(exclude_unset=True)

    # get/create any provided illustrators
    new_illustrators = []
    for illustrator_data in edition_data.illustrators or []:
        if isinstance(illustrator_data, int):
            new_illustrators.append(
                crud.illustrator.get_or_404(session, illustrator_data)
            )
        else:
            try:
                new_illustrators.append(
                    crud.illustrator.create(
                        session,
                        obj_in=IllustratorCreateIn(**dict(illustrator_data)),
                    )
                )
            except IntegrityError:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Illustrator {illustrator_data.first_name} {illustrator_data.last_name} already exists",
                )
    update_data["illustrators"] = new_illustrators

    # handle any provided cover image
    cover_url_data = edition_data.cover_url
    if cover_url_data:
        cover_url = (
            cover_url_data
            if is_url(cover_url_data)
            else handle_edition_cover_image_update(edition, cover_url_data, "wriveted")
        )
        if cover_url:
            update_data["cover_url"] = cover_url

    updated_edition = crud.edition.update(
        db=session, db_obj=edition, obj_in=update_data, merge_dicts=merge_dicts
    )

    changes_dict = edition_data.dict(exclude_unset=True, exclude_defaults=True)
    if new_url := changes_dict.get("cover_url"):
        if not is_url(new_url):
            changes_dict["cover_url"] = "[BASE64 IMAGE]"

    crud.event.create(
        session,
        title="Edition updated",
        description=f"Made a change to '{updated_edition.title}'",
        info={
            "changes": changes_dict,
            "title": updated_edition.title,
            "isbn": updated_edition.isbn,
        },
        account=account,
    )
    return updated_edition


@router.post("/editions")
async def bulk_add_editions(
    bulk_edition_data: List[EditionCreateIn],
    session: Session = Depends(get_session),
    account=Depends(get_current_active_user_or_service_account),
):
    isbns, created, existing = await create_missing_editions(
        session, new_edition_data=bulk_edition_data
    )
    msg = (
        f"Bulk load of {len(isbns)} editions complete. Created {created} new editions."
    )

    crud.event.create(
        session,
        title="Bulk editions added",
        description=msg,
        info={
            "created": created,
            "processed": len(isbns),
        },
        account=account,
    )

    return {"msg": msg}
