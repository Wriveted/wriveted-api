import uuid

from fastapi import Depends, Path, Query
from sqlalchemy.orm import Session

from app import crud
from app.db.session import get_session


def get_school_from_wriveted_id(
    wriveted_identifier: uuid.UUID = Path(
        ..., description="UUID representing a unique school in the Wriveted database"
    ),
    session: Session = Depends(get_session),
):
    return crud.school.get_by_wriveted_id_or_404(
        db=session, wriveted_id=wriveted_identifier
    )


def get_optional_school_from_wriveted_id_query(
    wriveted_identifier: uuid.UUID = Query(
        None, description="UUID representing a unique school in the Wriveted database"
    ),
    session: Session = Depends(get_session),
):
    if wriveted_identifier is None:
        return None
    else:
        return crud.school.get_by_wriveted_id_or_404(
            db=session, wriveted_id=wriveted_identifier
        )


def get_school_from_raw_id(
    id: str = Path(..., description="Raw sql integer id for school object"),
    session: Session = Depends(get_session),
):
    return crud.school.get_by_id_or_404(db=session, id=id)


# def get_school_from_path(
#    country_code: str = Path(
#        ...,
#        description="ISO 3166-1 Alpha-3 code for a country. E.g New Zealand is NZL, and Australia is AUS",
#    ),
#    school_id: str = Path(
#        ..., description="Official school Identifier. E.g in ACARA ID"
#    ),
#    session: Session = Depends(get_session),
# ):
#    return crud.school.get_by_official_id_or_404(
#        db=session, country_code=country_code, official_id=school_id
#    )
