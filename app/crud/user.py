from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session
from structlog import get_logger

from app.crud import CRUDBase
from app.models import User

from app.schemas.user import UserCreateIn, UserUpdateIn

logger = get_logger()


class CRUDUser(CRUDBase[User, UserCreateIn, UserUpdateIn]):

    # TODO handle create student account linked to school

    def get_or_create(self, db: Session, user_data: UserCreateIn, commit=True) -> User:
        """
        Get a user by email, creating a new user if required.
        """
        q = select(User).where(User.email == user_data.email)
        try:
            user = db.execute(q).scalar_one()
        except NoResultFound:
            logger.info("Creating new user", data=user_data)
            user = self.create(db, obj_in=user_data, commit=commit)
        return user

    def get_by_account_email(self, db: Session, email: str) -> Optional[User]:
        """ return User with given email (or account identifier) or None """
        return db.execute(select(User).where(User.email == email)).scalar_one_or_none()


user = CRUDUser(User)
