from typing import Optional, Tuple, List

from sqlalchemy import select, func
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session
from structlog import get_logger

from app.crud import CRUDBase
from app.models import User
from app.models.user import UserAccountType

from app.schemas.user import UserCreateIn, UserUpdateIn

logger = get_logger()


class CRUDUser(CRUDBase[User, UserCreateIn, UserUpdateIn]):

    # TODO handle create student account linked to school

    def get_or_create(self, db: Session, user_data: UserCreateIn, commit=True) -> Tuple[User, bool]:
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
        """ return User with given email (or account identifier) or None """
        return db.execute(select(User).where(User.email == email)).scalar_one_or_none()

    def get_all_with_optional_filters_query(
        self,
        db: Session,
        query_string: Optional[str] = None,
        type: Optional[UserAccountType] = None,
        is_active: Optional[bool] = None,
        students_of: Optional['School'] = None,
    ):
        user_query = self.get_all_query(db=db, order_by=User.name.asc())

        if query_string is not None:
            # https://docs.sqlalchemy.org/en/14/dialects/postgresql.html?highlight=search#full-text-search
            user_query = user_query.where(func.lower(User.name).contains(query_string.lower()))
        if type is not None:
            user_query = user_query.where(User.type == type)
        if is_active is not None:
            user_query = user_query.where(User.is_active == is_active)
        if students_of is not None:
            user_query = user_query.where(User.school_as_student == students_of)

        return user_query

    def get_all_with_optional_filters(
        self,
        db: Session,
        query_string: Optional[str] = None,
        type: Optional[UserAccountType] = None,
        is_active: Optional[bool] = None,
        students_of: Optional['School'] = None,
        skip: int = 0,
        limit: int = 100
    ):
        query = self.apply_pagination(
            self.get_all_with_optional_filters_query(
                db=db,
                query_string=query_string,
                type=type,
                is_active=is_active,
                students_of=students_of
            ),
            skip=skip, limit=limit
        )
        return db.execute(query).scalars().all()


user = CRUDUser(User)
