import enum
import uuid

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    JSON,
    Enum,
    Index,
    select,
    func,
    text
)
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship, column_property
from fastapi_permissions import (
    Allow,
    Deny,
)
from app.db import Base

from app.models.collection_item import CollectionItem
from app.models.service_account_school_association import service_account_school_association_table


class SchoolState(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    # Has initiated onboarding, a user has bound themselves to the school, but onboarding isn't yet completed.
    # Useful for email prompts to remind dropoff users to upload their collections, and other KPI metrics.
    PENDING = "pending"


class School(Base):

    id = Column(Integer, primary_key=True, autoincrement=True)

    country_code = Column(String(3), ForeignKey('countries.id', name="fk_school_country"), index=True)
    official_identifier = Column(String(512))

    # Used for public links to school pages e.g. chatbot
    wriveted_identifier = Column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        server_default=text('gen_random_uuid()'),
        index=True,
        unique=True,
        nullable=False
    )

    # Composite INDEX combining country code and country specific IDs e.g. (AUS, ACARA ID)
    Index("index_schools_by_country", country_code, official_identifier, unique=True)

    # Index combining country code and optional state stored in the location key of info.
    # Note alembic can't automatically deal with this, but the migration (and index) exists!
    #Index("index_schools_by_country_state", country_code, text("(info->'location'->>'state')"))

    state = Column(Enum(SchoolState), nullable=False, default=SchoolState.INACTIVE)

    name = Column(String(256), nullable=False)

    # e.g. "canterbury.ac.nz" if all student email addresses have the form
    # brian.thorne@canterbury.ac.nz - allows automatic registration
    student_domain = Column(String(256), nullable=True)

    # All users with this email domain will be granted teacher rights
    teacher_domain = Column(String(256), nullable=True)

    # Extra info:
    # school website
    # Suburb,State,Postcode,
    # Type,Sector,Status,Geolocation,
    # Parent School ID,AGE ID,
    # Latitude,Longitude
    info = Column(MutableDict.as_mutable(JSON))

    country = relationship('Country')

    collection = relationship('CollectionItem', lazy="dynamic", cascade="all, delete")

    # https://docs.sqlalchemy.org/en/14/orm/mapped_sql_expr.html#mapper-column-property-sql-expressions
    collection_count = column_property(
        select(func.count(CollectionItem.id))
            .where(CollectionItem.school_id == id)
            .correlate_except(CollectionItem)
            .scalar_subquery()
    )

    db_jobs = relationship('DbJob', cascade="all, delete-orphan")

    # https://docs.sqlalchemy.org/en/14/orm/extensions/associationproxy.html#simplifying-association-objects
    # association proxy of "collectionitems" collection
    # to "editions" attribute
    works = association_proxy('collection_items', 'work')
    editions = association_proxy('collection_items', 'edition')

    booklists = relationship("BookList", back_populates="school", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="school")
    users = relationship("User", back_populates="school")

    service_accounts = relationship(
        "ServiceAccount",
        secondary=service_account_school_association_table,
        back_populates="schools"
    )

    def __repr__(self):
        return f"<School '{self.name}' ({self.official_identifier} - {self.country.name})>"

    def __acl__(self):
        """ defines who can do what to the instance
        the function returns a list containing tuples in the form of
        (Allow or Deny, principal identifier, permission name)

        If a role is not listed (like "role:user") the access will be
        automatically denied.

        (Deny, Everyone, All) is automatically appended at the end.
        """
        return [
            # This would allow anyone logged in to view any school's collection
            #(Allow, Authenticated, "read"),

            (Allow, "role:admin", "create"),
            (Allow, "role:admin", "read"),
            (Allow, "role:admin", "update"),
            (Allow, "role:admin", "delete"),
            (Allow, "role:admin", "batch"),

            (Allow, "role:lms", "batch"),
            (Allow, "role:lms", "update"),
            (Allow, "role:lms", "read"),

            (Deny, "role:student", "update"),
            (Deny, "role:student", "delete"),

            (Allow, f"school:{self.id}", "read"),

            (Allow, f"school:{self.id}", "update"),
            (Allow, f"school:{self.id}", "update"),
        ]
