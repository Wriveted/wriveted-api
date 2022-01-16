from fastapi import HTTPException
from sqlalchemy import select, delete, update
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from app.crud import CRUDBase
from app.models import School, CollectionItem, User, Event
from app.schemas.school import SchoolCreateIn, SchoolUpdateIn


class CRUDSchool(CRUDBase[School, SchoolCreateIn, SchoolUpdateIn]):

    def get_by_official_id_or_404(self, db: Session, country_code: str, official_id: str):

        query = (
          select(School)
            .where(School.country_code == country_code.upper())
            .where(School.official_identifier == official_id)
        )
        try:
            return db.execute(query).scalar_one()
        except NoResultFound:
            raise HTTPException(
                status_code=404,
                detail=f"School with id {official_id} in {country_code} not found."
            )

    def remove(self, db: Session, *, obj_in: School):
        # To help the database out let's delete the collection first
        stmt = (
            delete(CollectionItem)
                .where(CollectionItem.school_id == obj_in.id)
        )
        db.execute(stmt)

        # Deactivate and unlink any users that were linked to this school
        # This seems safer than deleting them...
        stmt = (
            update(User)
                .where(User.school_id == obj_in.id)
                .values(school_id=None, is_active=False)
        )
        db.execute(stmt)

        # Delete any events that were linked to this school
        stmt = (
            delete(Event)
                .where(Event.school_id == obj_in.id)
        )
        db.execute(stmt)

        db.commit()
        # Now delete the school
        db.delete(obj_in)
        db.commit()
        return obj_in


school = CRUDSchool(School)