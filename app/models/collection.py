import uuid
from datetime import datetime

from fastapi_permissions import All, Allow
from sqlalchemy import JSON, DateTime, ForeignKey, String, func, select, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import column_property, mapped_column, relationship

from app.db import Base
from app.models.collection_item import CollectionItem


class Collection(Base):

    id = mapped_column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        unique=True,
        primary_key=True,
        index=True,
        nullable=False,
    )

    name = mapped_column(String(200), nullable=False, index=True)

    items = relationship(
        "CollectionItem", back_populates="collection", cascade="all, delete-orphan"
    )

    editions = association_proxy("items", "edition")
    works = association_proxy("items", "work")

    book_count = column_property(
        select(func.count(CollectionItem.id))
        .where(CollectionItem.collection_id == id)
        .correlate_except(CollectionItem)
        .scalar_subquery()
    )

    school_id = mapped_column(
        ForeignKey(
            "schools.wriveted_identifier",
            name="fk_school_collection",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )
    school = relationship("School", back_populates="collection")

    user_id = mapped_column(
        ForeignKey("users.id", name="fk_user_collection", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    user = relationship("User", back_populates="collection")

    info = mapped_column(MutableDict.as_mutable(JSON))
    created_at = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    def __repr__(self):
        def association_string():
            output = ""
            if self.school:
                output += f"school={self.school} "
            if self.user:
                output += f"user={self.user} "
            return output.strip()

        return f"<Collection '{self.name}' {association_string()} count={self.book_count} id={self.id}>"

    def __acl__(self):
        """
        Defines who can do what to the Collection instance.
        """

        policies = [
            (Allow, "role:admin", All),
            (Allow, "role:lms", All),
        ]

        if self.school:
            policies.append((Allow, f"school:{self.school.id}", "read"))
            policies.append((Allow, f"schooladmin:{self.school.id}", All))

        if self.user:
            policies.append((Allow, f"user:{self.user_id}", All))
            policies.append((Allow, f"parent:{self.user_id}", All))

        return policies
