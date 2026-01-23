"""
Illustrator Repository - Domain-focused data access for illustrators.

Migrated from app.crud.illustrator to follow repository pattern.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Sequence

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from app.models import Illustrator
from app.schemas.illustrator import IllustratorCreateIn


def first_last_to_name_key(first_name: str, last_name: str) -> str:
    """Generate normalized name key for illustrator lookup."""
    return "".join(
        char for char in f"{first_name or ''}{last_name}".lower() if char.isalnum()
    )


class IllustratorRepository(ABC):
    """Repository interface for Illustrator operations."""

    @abstractmethod
    def get_by_id(self, db: Session, illustrator_id: int) -> Optional[Illustrator]:
        """Get illustrator by ID."""
        pass

    @abstractmethod
    def get_or_404(self, db: Session, id: int) -> Illustrator:
        """Get illustrator by ID or raise 404."""
        pass

    @abstractmethod
    def get_all(
        self, db: Session, skip: int = 0, limit: int = 100
    ) -> Sequence[Illustrator]:
        """Get all illustrators with pagination."""
        pass

    @abstractmethod
    def get_or_create(
        self, db: Session, data: IllustratorCreateIn, commit: bool = True
    ) -> Illustrator:
        """Get existing illustrator or create new one."""
        pass

    @abstractmethod
    def create(
        self, db: Session, obj_in: IllustratorCreateIn, commit: bool = True
    ) -> Illustrator:
        """Create new illustrator."""
        pass

    @abstractmethod
    def create_in_bulk(
        self, db: Session, bulk_illustrator_data_in: List[IllustratorCreateIn]
    ) -> None:
        """Bulk upsert illustrators."""
        pass


class IllustratorRepositoryImpl(IllustratorRepository):
    """SQLAlchemy implementation of IllustratorRepository."""

    def get_by_id(self, db: Session, illustrator_id: int) -> Optional[Illustrator]:
        """Get illustrator by ID."""
        return db.get(Illustrator, illustrator_id)

    def get_or_404(self, db: Session, id: int) -> Illustrator:
        """Get illustrator by ID or raise HTTPException 404."""
        illustrator = self.get_by_id(db, id)
        if illustrator is None:
            raise HTTPException(
                status_code=404,
                detail=f"Illustrator with id {id} not found.",
            )
        return illustrator

    def get_all(
        self, db: Session, skip: int = 0, limit: int = 100
    ) -> Sequence[Illustrator]:
        """Get all illustrators with pagination."""
        query = (
            select(Illustrator).order_by(Illustrator.id.asc()).offset(skip).limit(limit)
        )
        return db.execute(query).scalars().all()

    def get_or_create(
        self, db: Session, data: IllustratorCreateIn, commit: bool = True
    ) -> Illustrator:
        """
        Get existing illustrator by name key or create new one.

        Uses name_key (normalized first+last name) for lookup to avoid duplicates.
        """
        q = select(Illustrator).where(
            Illustrator.name_key
            == first_last_to_name_key(data.first_name, data.last_name)
        )
        try:
            orm_obj = db.execute(q).scalar_one()
        except NoResultFound:
            orm_obj = self.create(db, obj_in=data, commit=commit)
        return orm_obj

    def create(
        self, db: Session, obj_in: IllustratorCreateIn, commit: bool = True
    ) -> Illustrator:
        """Create new illustrator."""
        orm_obj = Illustrator(
            first_name=obj_in.first_name,
            last_name=obj_in.last_name,
            info=obj_in.info or {},
        )
        db.add(orm_obj)
        if commit:
            db.commit()
            db.refresh(orm_obj)
        else:
            db.flush()
        return orm_obj

    def create_in_bulk(
        self, db: Session, bulk_illustrator_data_in: List[IllustratorCreateIn]
    ) -> None:
        """
        Bulk upsert illustrators using PostgreSQL INSERT ON CONFLICT.

        Note: Relies on assumption that illustrator names are unique (which may not be accurate).
        Uses on_conflict_do_nothing to skip duplicates silently.
        """
        insert_stmt = pg_insert(Illustrator).on_conflict_do_nothing()

        values = [
            {
                "first_name": illustrator.first_name,
                "last_name": illustrator.last_name,
                "info": {} if illustrator.info is None else illustrator.info,
            }
            for illustrator in bulk_illustrator_data_in
        ]
        db.execute(insert_stmt, values)
        db.flush()


# Create singleton instance for backward compatibility
illustrator_repository = IllustratorRepositoryImpl()
