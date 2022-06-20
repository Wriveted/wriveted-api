from typing import Any, Dict, Optional, Tuple, Union

from fastapi import Query
from fastapi.encoders import jsonable_encoder
from sqlalchemy import and_, func, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session
from structlog import get_logger

from app.crud import CRUDBase
from app.models import (
    Educator,
    Parent,
    PublicReader,
    SchoolAdmin,
    Student,
    User,
    WrivetedAdmin,
)
from app.models.school import School
from app.models.user import UserAccountType
from app.schemas.auth import SpecificUserDetail
from app.schemas.users.user_create import UserCreateIn
from app.schemas.users.user_update import UserUpdateIn
from app.services.users import new_identifiable_username

logger = get_logger()


class CRUDUser(CRUDBase[User, UserCreateIn, UserUpdateIn]):

    # TODO handle create student account linked to school

    # ----CRUD override----

    def get_query(self, db: Session, id: Any) -> Query:
        query = select(User).where(User.id == id)
        user = db.execute(query).scalar_one_or_none()

        if not user:
            return query

        match user.type:
            case UserAccountType.WRIVETED:
                return select(WrivetedAdmin).where(WrivetedAdmin.id == id)
            case UserAccountType.STUDENT:
                return select(Student).where(Student.id == id)
            case UserAccountType.PUBLIC:
                return select(PublicReader).where(PublicReader.id == id)
            case UserAccountType.EDUCATOR:
                return select(Educator).where(Educator.id == id)
            case UserAccountType.SCHOOL_ADMIN:
                return select(SchoolAdmin).where(SchoolAdmin.id == id)
            case UserAccountType.PARENT:
                return select(Parent).where(Parent.id == id)
            case _:
                return query

    def build_orm_object(self, obj_in: UserCreateIn, session: Session) -> User:
        """An uncommitted ORM object from the input data"""
        type = obj_in.type or UserAccountType.PUBLIC

        match type:
            case UserAccountType.PUBLIC:
                model = PublicReader
            case UserAccountType.STUDENT:
                model = Student
                self._generate_username_if_missing(session, obj_in)
            case UserAccountType.EDUCATOR:
                model = Educator
            case UserAccountType.SCHOOL_ADMIN:
                model = SchoolAdmin
            case UserAccountType.WRIVETED:
                model = WrivetedAdmin
            case UserAccountType.PARENT:
                model = Parent
            case _:
                model = User

        obj_in_data = jsonable_encoder(obj_in)

        # clean up None attributes
        obj_in_data = {k: v for k, v in obj_in_data.items() if v is not None}

        db_obj = model(**obj_in_data)
        return db_obj

    def _generate_username_if_missing(self, session, obj_in: UserCreateIn):
        if obj_in.username is None:
            obj_in.username = new_identifiable_username(
                obj_in.first_name, obj_in.last_name_initial, session, obj_in.school_id
            )

    # ---------------------

    def get_or_create(
        self, db: Session, user_data: UserCreateIn, commit=True
    ) -> Tuple[User, bool]:
        """
        Get a user by email, creating a new user if required.
        """
        q = select(User).where(User.email == user_data.email)
        try:
            user = db.execute(q).scalar_one()
            return user, False
        except NoResultFound:
            logger.info("Creating new user", data=user_data)
            user = self.create(db, obj_in=user_data, commit=commit)
            return user, True

    def get_by_account_email(self, db: Session, email: str) -> Optional[User]:
        """return User with given email (or account identifier) or None"""
        return db.execute(select(User).where(User.email == email)).scalar_one_or_none()

    def get_all_with_optional_filters_query(
        self,
        db: Session,
        query_string: Optional[str] = None,
        type: Optional[UserAccountType] = None,
        is_active: Optional[bool] = None,
        students_of: Optional["School"] = None,
    ):
        user_query = self.get_all_query(db=db, order_by=User.name.asc())

        if query_string is not None:
            # https://docs.sqlalchemy.org/en/14/dialects/postgresql.html?highlight=search#full-text-search
            user_query = user_query.where(
                func.lower(User.name).contains(query_string.lower())
            )
        if type is not None:
            user_query = user_query.where(User.type == type)
        if is_active is not None:
            user_query = user_query.where(User.is_active == is_active)
        if students_of is not None:
            user_query = (
                user_query.join(Student)
                .where(User.id == Student.id)
                .where(Student.school == students_of)
            )

        return user_query

    def get_filtered_with_count(
        self,
        db: Session,
        query_string: Optional[str] = None,
        type: Optional[UserAccountType] = None,
        is_active: Optional[bool] = None,
        students_of: Optional[School] = None,
        skip: int = 0,
        limit: int = 100,
    ):
        """
        Get users with optional filtering.

        :return: Tuple[int, list]
        Returns a count of the total matching rows, and the requested
        page of users.
        """
        select_statement = self.get_all_with_optional_filters_query(
            db=db,
            query_string=query_string,
            type=type,
            is_active=is_active,
            students_of=students_of,
        )
        matching_count = self.count_query(db=db, query=select_statement)

        paginated_users_query = self.apply_pagination(
            select_statement, skip=skip, limit=limit
        )

        return matching_count, db.scalars(paginated_users_query).all()

    def get_all_with_optional_filters(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        **kwargs,
    ):
        query = self.apply_pagination(
            self.get_all_with_optional_filters_query(db=db, **kwargs),
            skip=skip,
            limit=limit,
        )
        return db.execute(query).scalars().all()

    def get_student_by_username_and_school_id(
        self, db: Session, username: str, school_id: int
    ):
        q = select(Student).where(
            and_(
                func.lower(Student.username) == username.lower(),
                Student.school_id == school_id,
            )
        )
        return db.execute(q).scalar_one_or_none()

    # def update_user_type(self, db: Session, user: User, new_data: UserCreateIn):
    #     if user.type == new_data.type:
    #         return user

    #     match new_data.type:

    #         # if updating to SchoolAdmin
    #         case UserAccountType.SCHOOL_ADMIN:
    #             if user.type == UserAccountType.EDUCATOR:
    #                 # if the Educator prerequisites have already been met then
    #                 # we only need change the type and add a school_admins row
    #                 user.type = UserAccountType.SCHOOL_ADMIN
    #                 db.execute(insert(SchoolAdmin).values(id=user.id))
    #                 # always close the session after changing polymorphic entities
    #                 db.commit()
    #                 db.close()
    #             else
    #                 # otherwise we need to populate the Educator level as well
    #                 user.type = UserAccountType.SCHOOL_ADMIN
    #                 db.execute(insert(Educator).values())


user = CRUDUser(User)
