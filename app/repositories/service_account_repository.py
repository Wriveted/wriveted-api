"""
ServiceAccount repository - domain-focused data access for ServiceAccount domain.

Replaces the generic CRUDServiceAccount class with proper repository pattern.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import Select, select
from sqlalchemy.orm import Session
from structlog import get_logger

from app.models import ServiceAccount
from app.repositories.school_repository import school_repository
from app.schemas.school_identity import SchoolIdentity
from app.schemas.service_account import ServiceAccountCreateIn, ServiceAccountUpdateIn

logger = get_logger()


class ServiceAccountRepository(ABC):
    """Repository interface for ServiceAccount domain operations."""

    @abstractmethod
    def get(self, db: Session, id: UUID) -> Optional[ServiceAccount]:
        """Get a service account by its primary key ID."""
        pass

    @abstractmethod
    def create(
        self, db: Session, obj_in: ServiceAccountCreateIn, commit: bool = True
    ) -> ServiceAccount:
        """Create a new service account with associated schools."""
        pass

    @abstractmethod
    def update(
        self,
        db: Session,
        db_obj: ServiceAccount,
        obj_in: Union[ServiceAccountUpdateIn, Dict[str, Any]],
        commit: bool = True,
    ) -> ServiceAccount:
        """Update an existing service account."""
        pass

    @abstractmethod
    def set_access_to_schools(
        self, db: Session, svc_account: ServiceAccount, schools: List[SchoolIdentity]
    ) -> ServiceAccount:
        """Replace the service account's current associated schools with the provided list."""
        pass

    @abstractmethod
    def add_access_to_schools(
        self, db: Session, svc_account: ServiceAccount, schools: List[SchoolIdentity]
    ) -> ServiceAccount:
        """Add schools to the service account's access list."""
        pass

    @abstractmethod
    def get_or_404(self, db: Session, id: UUID) -> ServiceAccount:
        """Get a service account by ID or raise 404."""
        pass

    @abstractmethod
    def get_all_query(self, db: Session) -> Select:
        """Build a query to get all service accounts."""
        pass

    @abstractmethod
    def apply_pagination(self, query, skip: int = 0, limit: int = 100):
        """Apply pagination to a query."""
        pass

    @abstractmethod
    def remove(self, db: Session, id: UUID) -> ServiceAccount:
        """Delete a service account by ID."""
        pass


class ServiceAccountRepositoryImpl(ServiceAccountRepository):
    """Implementation of ServiceAccountRepository."""

    def get(self, db: Session, id: UUID) -> Optional[ServiceAccount]:
        """Get a service account by its primary key ID."""
        return db.get(ServiceAccount, id)

    def create(
        self, db: Session, obj_in: ServiceAccountCreateIn, commit: bool = True
    ) -> ServiceAccount:
        """Create a new service account with associated schools."""
        schools = []
        if obj_in.schools is not None:
            schools = list(obj_in.schools)

        obj_in.schools = []

        obj_in_data = obj_in.model_dump(exclude_unset=True)
        svc_account = ServiceAccount(**obj_in_data)
        db.add(svc_account)
        db.flush()

        self.add_access_to_schools(db, svc_account, schools)

        if commit:
            db.commit()
            db.refresh(svc_account)

        return svc_account

    def update(
        self,
        db: Session,
        db_obj: ServiceAccount,
        obj_in: Union[ServiceAccountUpdateIn, Dict[str, Any]],
        commit: bool = True,
    ) -> ServiceAccount:
        """Update an existing service account."""
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        schools = update_data.pop("schools", None)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)

        if schools is not None:
            self.set_access_to_schools(db=db, svc_account=db_obj, schools=schools)

        if commit:
            db.commit()
            db.refresh(db_obj)

        return db_obj

    def set_access_to_schools(
        self, db: Session, svc_account: ServiceAccount, schools: List[SchoolIdentity]
    ) -> ServiceAccount:
        """Replace the service account's current associated schools with the provided list."""
        svc_account.schools = []
        return self.add_access_to_schools(db, svc_account, schools)

    def add_access_to_schools(
        self, db: Session, svc_account: ServiceAccount, schools: List[SchoolIdentity]
    ) -> ServiceAccount:
        """Add schools to the service account's access list."""
        for school_identity in schools:
            school = school_repository.get_by_wriveted_id_or_404(
                db=db, wriveted_id=school_identity.wriveted_identifier
            )
            svc_account.schools.append(school)
        return svc_account

    def get_or_404(self, db: Session, id: UUID) -> ServiceAccount:
        """Get a service account by ID or raise HTTPException 404."""
        svc_account = self.get(db, id)
        if svc_account is None:
            raise HTTPException(
                status_code=404,
                detail=f"ServiceAccount with id {id} not found.",
            )
        return svc_account

    def get_all_query(self, db: Session) -> Select:
        """Build a query to get all service accounts."""
        return select(ServiceAccount)

    def apply_pagination(self, query, skip: int = 0, limit: int = 100):
        """Apply pagination to a query."""
        return query.offset(skip).limit(limit)

    def remove(self, db: Session, id: UUID) -> ServiceAccount:
        """Delete a service account by ID."""
        svc_account = self.get(db, id)
        if svc_account is not None:
            db.delete(svc_account)
            db.commit()
        return svc_account


# Singleton instance
service_account_repository = ServiceAccountRepositoryImpl()
