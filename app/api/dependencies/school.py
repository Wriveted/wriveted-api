from fastapi import Path, Depends
from sqlalchemy.orm import Session

from app import crud
from app.db.session import get_session


def get_school_from_path(
        country_code: str = Path(..., description="ISO 3166-1 Alpha-3 code for a country. E.g New Zealand is NZL, and Australia is AUS"),
        school_id: str = Path(..., description="Official school Identifier. E.g in ACARA ID"),
        session: Session = Depends(get_session)
):
    return crud.school.get_by_official_id_or_404(
        db=session,
        country_code=country_code,
        official_id=school_id
    )