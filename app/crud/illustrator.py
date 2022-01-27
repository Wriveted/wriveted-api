from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from app.crud import CRUDBase
from app.models import Illustrator
from app.schemas.illustrator import IllustratorCreateIn


class CRUDIllustrator(CRUDBase[Illustrator, Any, Any]):

    def get_or_create(self, db: Session, data: IllustratorCreateIn, commit=True) -> Illustrator:
        q = select(Illustrator).where(Illustrator.full_name == f"{data.last_name}, {data.first_name}")
        try:
            orm_obj = db.execute(q).scalar_one()
        except NoResultFound:
            orm_obj = self.create(db, obj_in=data, commit=commit)
        return orm_obj

illustrator = CRUDIllustrator(Illustrator)