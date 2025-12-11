"""
Product Repository - Domain-focused data access for products.

Migrated from app.crud.product to follow repository pattern.
"""

from abc import ABC, abstractmethod
from typing import Optional

from fastapi.encoders import jsonable_encoder
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.product import Product
from app.schemas.product import ProductCreateIn, ProductUpdateIn


class ProductRepository(ABC):
    """Repository interface for Product operations."""

    @abstractmethod
    def get_by_id(self, db: Session, product_id: str) -> Optional[Product]:
        """Get product by ID."""
        pass

    @abstractmethod
    def create(
        self, db: Session, obj_in: ProductCreateIn, commit: bool = True
    ) -> Product:
        """Create new product."""
        pass

    @abstractmethod
    def update(
        self,
        db: Session,
        db_obj: Product,
        obj_in: ProductUpdateIn,
        commit: bool = True,
    ) -> Product:
        """Update existing product."""
        pass

    @abstractmethod
    def upsert(self, db: Session, obj_in: ProductCreateIn, commit: bool = True):
        """Upsert a product (insert or do nothing on conflict)."""
        pass


class ProductRepositoryImpl(ProductRepository):
    """SQLAlchemy implementation of ProductRepository."""

    def get_by_id(self, db: Session, product_id: str) -> Optional[Product]:
        """Get product by ID."""
        return db.get(Product, product_id)

    def create(
        self, db: Session, obj_in: ProductCreateIn, commit: bool = True
    ) -> Product:
        """Create new product."""
        orm_obj = Product(**obj_in.dict())
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
        db_obj: Product,
        obj_in: ProductUpdateIn,
        commit: bool = True,
    ) -> Product:
        """Update existing product."""
        update_data = obj_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        if commit:
            db.commit()
            db.refresh(db_obj)
        else:
            db.flush()
        return db_obj

    def upsert(self, db: Session, obj_in: ProductCreateIn, commit: bool = True):
        """Upsert a product (insert or do nothing on conflict)."""
        upsert_stmt = (
            pg_insert(Product).values(jsonable_encoder(obj_in)).on_conflict_do_nothing()
        )
        db.execute(upsert_stmt)
        if commit:
            db.commit()


# Create singleton instance for backward compatibility
product_repository = ProductRepositoryImpl()
