from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from app.crud import CRUDBase
from app.models import ClassGroup, Event, School, Student
from app.models.collection import Collection
from app.models.educator import Educator
from app.models.school_admin import SchoolAdmin
from app.models.user import User, UserAccountType
from app.schemas.school import SchoolCreateIn, SchoolPatchOptions


class CRUDSchool(CRUDBase[School, SchoolCreateIn, SchoolPatchOptions]):
    def get_all_query_with_optional_filters(
        self,
        db: Session,
        country_code: Optional[str] = None,
        state: Optional[str] = None,
        postcode: Optional[str] = None,
        query_string: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_collection_connected: Optional[bool] = None,
        official_identifier: Optional[str] = None,
    ):
        school_query = self.get_all_query(db)
        if country_code is not None:
            school_query = school_query.where(School.country_code == country_code)
        if state is not None:
            school_query = school_query.where(
                School.info["location", "state"].as_string() == state
            )
        if postcode is not None:
            school_query = school_query.where(
                School.info["location", "postcode"].as_string() == postcode
            )
        if query_string is not None:
            # https://docs.sqlalchemy.org/en/14/dialects/postgresql.html?highlight=search#full-text-search
            school_query = school_query.where(
                func.lower(School.name).contains(query_string.lower())
            )
        if is_active is not None:
            school_query = school_query.where(
                School.state == ("active" if is_active else "inactive")
            )
        if is_collection_connected is not None:
            school_query = school_query.join(Collection).where(
                Collection.book_count > 0
            )
        if official_identifier is not None:
            school_query = school_query.where(
                School.official_identifier == official_identifier
            )
        return school_query

    def get_all_with_optional_filters(
        self,
        db: Session,
        country_code: Optional[str] = None,
        state: Optional[str] = None,
        postcode: Optional[str] = None,
        query_string: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_collection_connected: Optional[bool] = None,
        official_identifier: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[School]:
        query = self.apply_pagination(
            self.get_all_query_with_optional_filters(
                db,
                country_code=country_code,
                state=state,
                postcode=postcode,
                query_string=query_string,
                is_active=is_active,
                is_collection_connected=is_collection_connected,
                official_identifier=official_identifier,
            ),
            skip=skip,
            limit=limit,
        )
        return db.execute(query).scalars().all()

    def get_by_official_id_or_404(
        self, db: Session, country_code: str, official_id: str
    ):
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
                detail=f"School with id {official_id} in {country_code} not found.",
            )

    def get_by_wriveted_id_or_404(self, db: Session, wriveted_id: str):
        query = select(School).where(School.wriveted_identifier == wriveted_id)
        try:
            return db.execute(query).scalar_one()
        except NoResultFound:
            raise HTTPException(
                status_code=404,
                detail=f"School with wriveted_id {wriveted_id} not found.",
            )

    def remove(self, db: Session, *, obj_in: School):
        # To help the database out let's delete the collection first
        stmt = delete(Collection).where(
            Collection.school_id == obj_in.wriveted_identifier
        )
        db.execute(stmt)

        # Convert any students from this school to PublicReader,
        # then delete the Student-level data (preserving the Reader level)
        demote_students = (
            update(User)
            .where(
                User.id.in_(select(Student.id).where(Student.school_id == obj_in.id))
            )
            .values(type=UserAccountType.PUBLIC, is_active=False)
            .execution_options(synchronize_session=False)
        )

        db.execute(demote_students)

        # DB should do this on school deletion via Cascade
        delete_students = delete(Student).where(Student.school_id == obj_in.id)
        db.execute(delete_students)
        # Now the students are deleted... remove the classes
        stmt = delete(ClassGroup).where(
            ClassGroup.school_id == obj_in.wriveted_identifier
        )
        db.execute(stmt)

        # Do the same with SchoolAdmins.
        # Work from the lowest level of inheritance up, preserving User data at the top
        demote_schooladmins = (
            update(User)
            .where(
                User.id.in_(
                    select(SchoolAdmin.id).where(SchoolAdmin.school_id == obj_in.id)
                )
            )
            .values(type=UserAccountType.PUBLIC, is_active=False)
            .execution_options(synchronize_session=False)
        )

        db.execute(demote_schooladmins)
        # delete_schooladmins = delete(SchoolAdmin).where(
        #     SchoolAdmin.school_id == obj_in.id
        # )
        # db.execute(delete_schooladmins)

        # and Educators in general
        demote_educators = (
            update(User)
            .where(
                User.id.in_(select(Educator.id).where(Educator.school_id == obj_in.id))
            )
            .values(type=UserAccountType.PUBLIC, is_active=False)
            .execution_options(synchronize_session=False)
        )
        db.execute(demote_educators)
        # delete_educators = delete(Educator).where(Educator.school_id == obj_in.id)
        # db.execute(delete_educators)

        # Delete any events that were linked to this school
        stmt = delete(Event).where(Event.school_id == obj_in.id)
        db.execute(stmt)
        print("Deleting database objects related to the school")
        db.commit()
        print("Deleting the school", obj_in)
        # Now delete the school
        db.execute(
            delete(School)
            .where(School.wriveted_identifier == obj_in.wriveted_identifier)
            .execution_options(synchronize_session=False)
        )
        db.commit()
        return obj_in

    def get_by_id_or_404(self, db: Session, id: int):
        query = select(School).where((School.id) == (id))
        try:
            return db.execute(query).scalar_one()
        except NoResultFound:
            raise HTTPException(
                status_code=404, detail=f"School with id {id} not found."
            )


school = CRUDSchool(School)
