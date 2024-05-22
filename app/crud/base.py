from typing import Any, Dict, Generic, List, Optional, Sequence, Type, TypeVar, Union

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy import Select, delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Query, Session, aliased

from app.db import Base

T = TypeVar("T")
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

    def get_query(self, db: Session, id: Any) -> Select[ModelType]:
        return select(self.model).where(self.model.id == id)

    async def aget_query(self, db: AsyncSession, id: Any) -> Select[ModelType]:
        # Usually the same as get_query, but can be overridden if needed (see User)
        return self.get_query(db, id=id)

    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        """return object with given id or None"""
        return db.execute(self.get_query(db=db, id=id)).scalar_one_or_none()

    async def aget(self, db: AsyncSession, id: Any) -> Optional[ModelType]:
        """return object with given id or None"""
        query = await self.aget_query(db, id=id)
        return (await db.execute(query)).scalar_one_or_none()

    def get_or_404(self, db: Session, id: Any) -> ModelType:
        """raises an HTTPException if object is not found."""
        thing = self.get(db, id=id)
        if thing is None:
            raise HTTPException(
                status_code=404,
                detail=f"Resource {self.model.__name__} with id {id} not found.",
            )
        return thing

    async def aget_or_404(self, db: AsyncSession, id: Any) -> ModelType:
        """raises an HTTPException if object is not found."""
        thing = await self.aget(db, id=id)
        if thing is None:
            raise HTTPException(
                status_code=404,
                detail=f"Resource {self.model.__name__} with id {id} not found.",
            )
        return thing

    def get_all_query(self, db: Session, *, order_by=None) -> Select[ModelType]:
        """Return select statement for all objects of this model

        Query the model's table returning a sqlalchemy Query object so that
        filters can be applied before emitting the final SQL statement.

        One potential gotcha is applying pagination (offset and limit calls) must occur
        after all filters. You can't call filters after the ``apply_pagination`` static
        method.
        """
        direction = order_by if order_by is not None else self.model.id.asc()
        stmt = select(self.model)
        if isinstance(direction, list):
            stmt = stmt.order_by(*direction)
        else:
            stmt = stmt.order_by(direction)
        return stmt

    def get_multi_query(
        self, db: Session, ids: List[Any], *, order_by=None
    ) -> Select[ModelType]:
        """Return Query for objects of this model with given ids
        Query the model's table returning a sqlalchemy Query object so that
        filters can be applied before emitting the final SQL statement.

        One potential gotcha is applying pagination (offset and limit calls) must occur
        after all filters. You can't call filters after the ``apply_pagination`` static
        method.
        """
        return self.get_all_query(db, order_by=order_by).where(self.model.id.in_(ids))

    @staticmethod
    def apply_pagination(
        query: Select[T], *, skip: int = None, limit: int = None
    ) -> Select[T]:
        return query.offset(skip).limit(limit)

    def count_query(self, db: Session, query) -> int:
        cte = query.cte()
        aliased_model = aliased(self.model, cte)
        return db.scalar(select(func.count(aliased_model.id)))

    def count_all(self, db: Session) -> int:
        return db.scalar(select(func.count(self.model.id)))

    def get_all(
        self, db: Session, *, skip: int = 0, limit: int = 100, order_by=None
    ) -> Sequence[ModelType]:
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
    ) -> Sequence[ModelType]:
        """return objects of this model with given ids"""
        query = self.apply_pagination(
            self.get_multi_query(db=db, ids=ids, order_by=order_by),
            skip=skip,
            limit=limit,
        )
        return db.scalars(query).all()

    def create(
        self, db: Session, *, obj_in: CreateSchemaType, commit=True
    ) -> ModelType:
        db_obj = self.build_orm_object(obj_in, session=db)
        db.add(db_obj)

        if commit:
            db.commit()
            db.refresh(db_obj)
        return db_obj

    def build_orm_object(self, obj_in: CreateSchemaType, session: Session) -> ModelType:
        """An uncommitted ORM object from the input data"""
        obj_in_data = jsonable_encoder(obj_in)
        db_obj = self.model(**obj_in_data)  # type: ignore
        return db_obj

    def create_in_bulk(self, db: Session, *, bulk_mappings_in):
        stmt = insert(self.model).values(bulk_mappings_in)
        db.execute(stmt)

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]],
        merge_dicts: bool = False,
        commit: bool = True,
    ) -> ModelType:
        self._update_internal(db_obj, merge_dicts, obj_in)

        db.add(db_obj)
        if commit:
            db.commit()
            db.refresh(db_obj)
        return db_obj

    async def aupdate(
        self,
        session: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]],
        merge_dicts: bool = False,
        commit: bool = True,
    ) -> ModelType:
        self._update_internal(db_obj, merge_dicts, obj_in)

        session.add(db_obj)
        if commit:
            await session.commit()
            await session.refresh(db_obj)
        return db_obj

    def _update_internal(self, db_obj, merge_dicts, obj_in):
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        for field in update_data:
            if hasattr(db_obj, field):
                attr = getattr(db_obj, field)
                if merge_dicts and isinstance(attr, dict):
                    deep_merge_dicts(attr, update_data[field])
                else:
                    setattr(db_obj, field, update_data[field])
                if isinstance(attr, MutableDict):
                    # If only a nested field has been altered, SQLAlchemy won't know about it!
                    attr.changed()

    def remove(self, db: Session, *, id: Any) -> ModelType:
        obj = self.get(db=db, id=id)
        if obj is not None:
            db.delete(obj)
            db.commit()
        return obj

    def remove_multi(self, db: Session, *, ids: Query):
        delete(self.model).where(self.model.id.in_(ids)).delete(
            synchronize_session="fetch"
        )
        db.commit()


def deep_merge_dicts(original, incoming):
    """
    Thanks Vikas https://stackoverflow.com/a/50773244
    Deep merge two dictionaries. Modifies original.
    """
    for key in incoming:
        if key in original:
            if isinstance(original[key], dict) and isinstance(incoming[key], dict):
                deep_merge_dicts(original[key], incoming[key])
            else:
                original[key] = incoming[key]
        else:
            original[key] = incoming[key]


def compare_dicts(dict1, dict2):
    diff = {}
    for key in set(dict1.keys()).union(dict2.keys()):
        if key.startswith("_") or (
            isinstance(dict1.get(key), dict)
            and any(k.startswith("_") for k in dict1[key])
        ):
            continue
        if isinstance(dict1.get(key), dict) and isinstance(dict2.get(key), dict):
            sub_diff = compare_dicts(dict1[key], dict2[key])
            if sub_diff:
                diff[key] = sub_diff
        elif dict1.get(key) != dict2.get(key):
            diff[key] = (dict1.get(key), dict2.get(key))
    return diff
