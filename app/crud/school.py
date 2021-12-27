from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from app.crud import CRUDBase
from app.models import School
from app.schemas.school import SchoolCreateIn, SchoolUpdateIn


class CRUDSchool(CRUDBase[School, SchoolCreateIn, SchoolUpdateIn]):

    def get_by_official_id_or_404(self, db: Session, country_code: str, official_id: str):
        query = (
            select(School)
            .where(School.country_code == country_code)
            .where(School.official_identifier == official_id)
        )
        try:
            return db.execute(query).scalar_one()
        except NoResultFound:
            raise HTTPException(
                status_code=404,
                detail=f"School with id {official_id} in {country_code} not found."
            )

