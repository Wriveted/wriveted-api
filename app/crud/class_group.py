from typing import List, Optional
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.crud import CRUDBase
from app.models import School, Student
from app.models.class_group import ClassGroup
from app.schemas.class_group import ClassGroupCreateIn, ClassGroupUpdateIn
from app.services.class_groups import new_random_class_code


class CRUDClassGroup(CRUDBase[ClassGroup, ClassGroupCreateIn, ClassGroupUpdateIn]):
    def get_all_query_with_optional_filters(
        self,
        db: Session,
        school: Optional[School] = None,
        query_string: Optional[str] = None,
    ):
        class_group_query = self.get_all_query(db)

        if school is not None:
            class_group_query = class_group_query.where(ClassGroup.school == school)

        if query_string is not None:
            class_group_query = class_group_query.where(
                func.lower(ClassGroup.name).contains(query_string.lower())
            )

        return class_group_query

    def get_all_with_optional_filters(
        self,
        db: Session,
        school: Optional[School] = None,
        query_string: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ClassGroup]:
        query = self.apply_pagination(
            self.get_all_query_with_optional_filters(
                db, school=school, query_string=query_string
            ),
            skip=skip,
            limit=limit,
        )

        return db.scalars(query).all()

    def get_by_class_code(self, db: Session, code: str) -> Optional[ClassGroup]:
        """return ClassGroup with given class join code or None"""
        return db.execute(
            select(ClassGroup).where(ClassGroup.join_code == code)
        ).scalar_one_or_none()

    def build_orm_object(
        self, obj_in: ClassGroupCreateIn, session: Session
    ) -> ClassGroup:
        """An uncommitted ORM object from the input data"""

        return ClassGroup(
            name=obj_in.name,
            school_id=obj_in.school_id,
            join_code=new_random_class_code(session),
        )

    def remove(self, db: Session, *, id: UUID) -> ClassGroup:
        # To help the database out let's remove the students first
        # DB should do this on class deletion via Cascade
        stmt = delete(Student).where(Student.class_group_id == id)
        db.execute(stmt)
        return super().remove(db, id=id)


class_group = CRUDClassGroup(ClassGroup)
