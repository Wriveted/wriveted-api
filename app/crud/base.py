from typing import Any, Dict, Generic, List, Optional, Sequence, Type, TypeVar, Union

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy import Select, delete, func, insert, select
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Query, Session, aliased
from app.api.common.pagination import PaginationOrderingError

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

    def get_query(self, db: Session, id: Any) -> Select[ModelType]:
        return select(self.model).where(self.model.id == id)

    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        """return object with given id or None"""
        return db.execute(self.get_query(db=db, id=id)).scalar_one_or_none()

    def get_or_404(self, db: Session, id: Any) -> ModelType:
        """raises an HTTPException if object is not found."""
        thing = self.get(db, id=id)
        if thing is None:
            raise HTTPException(
                status_code=404,
                detail=f"Resource {self.model.__name__} with id {id} not found.",
            )
        return thing

    def get_all_query(self, db: Session) -> Select[ModelType]:
        """Return select statement for all objects of this model

        Query the model's table returning a sqlalchemy Query object so that
        filters can be applied before emitting the final SQL statement.

        One potential gotcha is applying pagination (offset and limit calls) must occur
        after all filters. You can't call filters after the ``apply_pagination`` static
        method.
        """
        return select(self.model)

    def get_multi_query(self, db: Session, ids: List[Any]) -> Select[ModelType]:
        """Return Query for objects of this model with given ids
        Query the model's table returning a sqlalchemy Query object so that
        filters can be applied before emitting the final SQL statement.

        One potential gotcha is applying pagination (offset and limit calls) must occur
        after all filters. You can't call filters after the ``apply_pagination`` static
        method.
        """
        return self.get_all_query(db).where(self.model.id.in_(ids))

    @staticmethod
    def apply_pagination(
        query: Select[ModelType],
        *,
        skip: int = None,
        limit: int = None,
        order_by: str = None,
        order_by_table: str = None,
        order_direction: str = None,
    ) -> Select[ModelType]:
        """Apply pagination (limit, skip, order_by, order_by_table, order_direction) to a query.
        Raises: [`PaginationOrderingError` if order_by is not a column of the constructed query, the specified table is not part of the constructed query, or the specified column exists, but is not sortable]
        """
        if order_by_table is not None:
            # check if the table name has been included in the query
            if order_by_table not in [col.table.name for col in query.selected_columns]:
                raise PaginationOrderingError(
                    f"No such table {order_by_table} in query"
                )

        if order_by is not None:
            # check if the column name is in the query, with the correct table name if specified
            for col in query.selected_columns:
                if (
                    col.table.name == order_by_table or not order_by_table
                ) and col.name == order_by:
                    col_clause = col.expression
                    # if not col_clause.comparator.type.sort_key_function:
                    #     raise PaginationOrderingError(
                    #         f"Column {order_by} is not sortable in query"
                    #     )
                    if order_direction.lower() == "desc":
                        query = query.order_by(col_clause.desc())
                    else:
                        query = query.order_by(col_clause.asc())
                    break
            else:
                raise PaginationOrderingError(f"No such column {order_by} in query")

        return query.offset(skip).limit(limit)

    def count_query(self, db: Session, query) -> int:
        cte = query.cte()
        aliased_model = aliased(self.model, cte)
        return db.scalar(select(func.count(aliased_model.id)))

    def count_all(self, db: Session) -> int:
        return db.scalar(select(func.count(self.model.id)))

    def get_all(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        order_by: str = None,
        order_direction: str = None,
    ) -> Sequence[ModelType]:
        """return all objects of this model"""
        query = self.apply_pagination(
            self.get_all_query(db=db, order_by=order_by),
            skip=skip,
            limit=limit,
            order_by=order_by,
            order_direction=order_direction,
        )
        return db.scalars(query).all()

    def get_multi(
        self,
        db: Session,
        ids: List[Any],
        *,
        skip: int = 0,
        limit: int = 100,
        order_by: str = None,
        order_direction: str = None,
    ) -> Sequence[ModelType]:
        """return objects of this model with given ids"""
        query = self.apply_pagination(
            self.get_multi_query(db=db, ids=ids),
            skip=skip,
            limit=limit,
            order_by=order_by,
            order_direction=order_direction,
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

        db.add(db_obj)
        if commit:
            db.commit()
            db.refresh(db_obj)
        return db_obj

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
