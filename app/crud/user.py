from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound, MultipleResultsFound
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


user = CRUDUser(User)
