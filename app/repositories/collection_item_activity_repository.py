"""
CollectionItemActivity Repository - Domain-focused data access for collection item activities.

Migrated from app.crud.collection_item_activity to follow repository pattern.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models import Reader
from app.models.collection_item_activity import (
    CollectionItemActivity,
    CollectionItemReadStatus,
)
from app.schemas.collection import CollectionItemActivityBase


class CollectionItemActivityRepository(ABC):
    """Repository interface for CollectionItemActivity operations."""

    @abstractmethod
    def get_by_id(
        self, db: Session, activity_id: int
    ) -> Optional[CollectionItemActivity]:
        """Get collection item activity by ID."""
        pass

    @abstractmethod
    def search(
        self,
        db: Session,
        collection_item_id: Optional[int] = None,
        reader: Optional[Reader] = None,
        status: Optional[CollectionItemReadStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[CollectionItemActivity]:
        """Search collection item activities with optional filters."""
        pass

    @abstractmethod
    def create(
        self, db: Session, obj_in: CollectionItemActivityBase, commit: bool = True
    ) -> CollectionItemActivity:
        """Create new collection item activity."""
        pass


class CollectionItemActivityRepositoryImpl(CollectionItemActivityRepository):
    """SQLAlchemy implementation of CollectionItemActivityRepository."""

    def get_by_id(
        self, db: Session, activity_id: int
    ) -> Optional[CollectionItemActivity]:
        """Get collection item activity by ID."""
        return db.get(CollectionItemActivity, activity_id)

    def search(
        self,
        db: Session,
        collection_item_id: Optional[int] = None,
        reader: Optional[Reader] = None,
        status: Optional[CollectionItemReadStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[CollectionItemActivity]:
        """
        Search collection item activities with optional filters.

        Args:
            db: Database session
            collection_item_id: Optional collection item ID to filter by
            reader: Optional reader to filter by
            status: Optional read status to filter by
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return

        Returns:
            List of matching collection item activities
        """
        from sqlalchemy import select

        query = select(CollectionItemActivity).order_by(
            CollectionItemActivity.timestamp.desc()
        )

        if collection_item_id is not None:
            query = query.where(
                CollectionItemActivity.collection_item_id == collection_item_id
            )
        if reader is not None:
            query = query.where(CollectionItemActivity.reader == reader)
        if status is not None:
            query = query.where(CollectionItemActivity.status == status)

        query = query.offset(skip).limit(limit)
        return list(db.scalars(query).all())

    def create(
        self, db: Session, obj_in: CollectionItemActivityBase, commit: bool = True
    ) -> CollectionItemActivity:
        """Create new collection item activity."""
        orm_obj = CollectionItemActivity(**obj_in.dict())
        db.add(orm_obj)
        if commit:
            db.commit()
            db.refresh(orm_obj)
        else:
            db.flush()
        return orm_obj


# Create singleton instance for backward compatibility
collection_item_activity_repository = CollectionItemActivityRepositoryImpl()
