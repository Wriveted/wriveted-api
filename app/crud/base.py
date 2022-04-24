from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy import select, delete, func
from sqlalchemy.orm import Session, Query, aliased

from app.db import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        """
        CRUD object with default methods to Create, Read, Update, Delete (CRUD).

        **Parameters**

        * `model`: A SQLAlchemy model class
        * `schema`: A Pydantic model (schema) class
        """
        self.model = model

    def get_query(self, db: Session, id: Any) -> Query:
        return select(self.model).where(self.model.id == id)

    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        """return object with given id or None"""
        return db.execute(self.get_query(db=db, id=id)).scalar_one_or_none()

    def get_or_404(self, db: Session, id: Any) -> ModelType:
        """ " raises an HTTPException if object is not found."""
        thing = self.get(db, id=id)
        if thing is None:
            raise HTTPException(
                status_code=404,
                detail=f"Resource {self.model.__name__} with id {id} not found.",
            )
        return thing

    def get_all_query(self, db: Session, *, order_by=None) -> Query:
        """Return select statement for all objects of this model

        Query the model's table returning a sqlalchemy Query object so that
        filters can be applied before emitting the final SQL statement.

        One potential gotcha is applying pagination (offset and limit calls) must occur
        after all filters. You can't call filters after the ``apply_pagination`` static
        method.
        """
        direction = order_by if order_by is not None else self.model.id.asc()
        return select(self.model).order_by(direction)

    def get_multi_query(self, db: Session, ids: List[Any], *, order_by=None) -> Query:
        """Return Query for objects of this model with given ids
        Query the model's table returning a sqlalchemy Query object so that
        filters can be applied before emitting the final SQL statement.

        One potential gotcha is applying pagination (offset and limit calls) must occur
        after all filters. You can't call filters after the ``apply_pagination`` static
        method.
        """
        return self.get_all_query(db, order_by=order_by).where(self.model.id.in_(ids))

    @staticmethod
    def apply_pagination(query: Query, *, skip: int = None, limit: int = None):
        return query.offset(skip).limit(limit)

    def count_all(self, db: Session) -> int:
        return db.scalar(select(func.count(self.model.id)))

    def get_all(
        self, db: Session, *, skip: int = 0, limit: int = 100, order_by=None
    ) -> List[ModelType]:
        """return all objects of this model"""
        query = self.apply_pagination(
            self.get_all_query(db=db, order_by=order_by), skip=skip, limit=limit
        )
        return db.scalars(query).all()

    def get_multi(
        self,
        db: Session,
        ids: List[Any],
        *,
        skip: int = 0,
        limit: int = 100,
        order_by=None,
    ) -> List[ModelType]:
        """return objects of this model with given ids"""
        query = self.apply_pagination(
            self.get_multi_query(db=db, ids=ids, order_by=order_by),
            skip=skip,
            limit=limit,
        )
        return db.execute(query).scalars().all()

    def create(
        self, db: Session, *, obj_in: CreateSchemaType, commit=True
    ) -> ModelType:
        db_obj = self.build_orm_object(obj_in)
        db.add(db_obj)

        if commit:
            db.commit()
            db.refresh(db_obj)
        return db_obj

    def build_orm_object(self, obj_in: CreateSchemaType) -> ModelType:
        """An uncommitted ORM object from the input data"""
        obj_in_data = jsonable_encoder(obj_in)
        db_obj = self.model(**obj_in_data)  # type: ignore
        return db_obj

    def create_in_bulk(self, db: Session, *, bulk_mappings_in):
        db.bulk_insert_mappings(self.model, bulk_mappings_in)

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]],
    ) -> ModelType:

        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        for field in update_data:
            if hasattr(db_obj, field):
                setattr(db_obj, field, update_data[field])
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: Any) -> ModelType:
        obj = self.get(db=db, id=id)
        db.delete(obj)
        db.commit()
        return obj

    def remove_multi(self, db: Session, *, ids: Query):
        delete(self.model).where(self.model.id.in_(ids)).delete(
            synchronize_session="fetch"
        )
        db.commit()
