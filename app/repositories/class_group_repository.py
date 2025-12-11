"""
ClassGroup Repository - Domain-focused data access for class groups.

Migrated from app.crud.class_group to follow repository pattern.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import ClassGroup, School, Student
from app.schemas.class_group import ClassGroupCreateIn, ClassGroupUpdateIn


class ClassGroupRepository(ABC):
    """Repository interface for ClassGroup operations."""

    @abstractmethod
    def get_by_id(self, db: Session, class_group_id: UUID) -> Optional[ClassGroup]:
        """Get class group by ID."""
        pass

    @abstractmethod
    def get_or_404(self, db: Session, class_group_id: UUID) -> ClassGroup:
        """Get class group by ID or raise 404 HTTPException."""
        pass

    @abstractmethod
    def get_by_class_code(self, db: Session, code: str) -> Optional[ClassGroup]:
        """Get class group by join code."""
        pass

    @abstractmethod
    def search(
        self,
        db: Session,
        school: Optional[School] = None,
        query_string: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ClassGroup]:
        """Search class groups with optional filters."""
        pass

    @abstractmethod
    def create(
        self, db: Session, obj_in: ClassGroupCreateIn, commit: bool = True
    ) -> ClassGroup:
        """Create new class group."""
        pass

    @abstractmethod
    def update(
        self,
        db: Session,
        db_obj: ClassGroup,
        obj_in: ClassGroupUpdateIn,
        commit: bool = True,
    ) -> ClassGroup:
        """Update existing class group."""
        pass

    @abstractmethod
    def remove(self, db: Session, id: UUID) -> ClassGroup:
        """Remove class group and cascade delete students."""
        pass


class ClassGroupRepositoryImpl(ClassGroupRepository):
    """SQLAlchemy implementation of ClassGroupRepository."""

    def get_by_id(self, db: Session, class_group_id: UUID) -> Optional[ClassGroup]:
        """Get class group by ID."""
        return db.get(ClassGroup, class_group_id)

    def get_or_404(self, db: Session, class_group_id: UUID) -> ClassGroup:
        """
        Get class group by ID or raise 404 HTTPException.

        Note: This method exists for backward compatibility with CRUD pattern.
        In clean architecture, repositories should not raise HTTP exceptions.
        """
        class_group = self.get_by_id(db, class_group_id)
        if class_group is None:
            raise HTTPException(
                status_code=404,
                detail=f"Resource ClassGroup with id {class_group_id} not found.",
            )
        return class_group

    def get_by_class_code(self, db: Session, code: str) -> Optional[ClassGroup]:
        """Get class group by join code."""
        return db.execute(
            select(ClassGroup).where(ClassGroup.join_code == code)
        ).scalar_one_or_none()

    def search(
        self,
        db: Session,
        school: Optional[School] = None,
        query_string: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ClassGroup]:
        """
        Search class groups with optional filters.

        Args:
            db: Database session
            school: Optional school to filter by
            query_string: Optional search string to filter by name
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return

        Returns:
            List of matching class groups
        """
        query = select(ClassGroup)

        if school is not None:
            query = query.where(ClassGroup.school == school)

        if query_string is not None:
            query = query.where(
                func.lower(ClassGroup.name).contains(query_string.lower())
            )

        query = query.offset(skip).limit(limit)
        return list(db.scalars(query).all())

    def create(
        self, db: Session, obj_in: ClassGroupCreateIn, commit: bool = True
    ) -> ClassGroup:
        """Create new class group with generated join code."""
        from app.services.class_groups import new_random_class_code

        orm_obj = ClassGroup(
            name=obj_in.name,
            school_id=obj_in.school_id,
            join_code=new_random_class_code(db),
        )
        db.add(orm_obj)
        if commit:
            db.commit()
            db.refresh(orm_obj)
        else:
            db.flush()
        return orm_obj

    def update(
        self,
        db: Session,
        db_obj: ClassGroup,
        obj_in: ClassGroupUpdateIn,
        commit: bool = True,
    ) -> ClassGroup:
        """Update existing class group."""
        update_data = obj_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        if commit:
            db.commit()
            db.refresh(db_obj)
        else:
            db.flush()
        return db_obj

    def remove(self, db: Session, id: UUID) -> ClassGroup:
        """
        Remove class group and cascade delete students.

        Explicitly deletes students first to help the database,
        even though cascade should handle this.
        """
        stmt = delete(Student).where(Student.class_group_id == id)
        db.execute(stmt)

        class_group = self.get_by_id(db, id)
        if class_group:
            db.delete(class_group)
            db.commit()
        return class_group


# Create singleton instance for backward compatibility
class_group_repository = ClassGroupRepositoryImpl()
