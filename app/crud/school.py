from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import select, delete, update
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from app.crud import CRUDBase
from app.models import School, CollectionItem, User, Event
from app.schemas.school import SchoolCreateIn, SchoolUpdateIn


class CRUDSchool(CRUDBase[School, SchoolCreateIn, SchoolUpdateIn]):

    def get_all_query_with_optional_filters(
            self,
            db: Session,
            country_code: Optional[str] = None,
            query_string: Optional[str] = None
    ):
        school_query = self.get_all_query(db)
        if country_code is not None:
            school_query = school_query.where(School.country_code == country_code)
        if query_string is not None:
            # https://docs.sqlalchemy.org/en/14/dialects/postgresql.html?highlight=search#full-text-search
            school_query = school_query.where(School.name.contains(query_string))

        return school_query

    def get_all_with_optional_filters(
        self,
        db: Session,
        country_code: Optional[str] = None,
        query_string: Optional[str] = None
    ) -> List[School]:
        query = self.get_all_query_with_optional_filters(db, country_code=country_code, query_string=query_string)
        return db.execute(query).scalars().all()

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