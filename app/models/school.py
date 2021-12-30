import enum
from sqlalchemy import (
    Column,
    Computed,
    ForeignKey,
    Integer,
    String,
    JSON,
    Enum, UniqueConstraint, Index
)
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import relationship
from fastapi_permissions import (
    Allow,
    Authenticated,
    Deny,
    Everyone,
    configure_permissions,
    list_permissions,
)
from app.db import Base



from app.models.service_account_school_association import service_account_school_association_table


class SchoolState(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class School(Base):

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Composite INDEX combining country code and country specific IDs e.g. (AUS, ACARA ID)
    country_code = Column(String(3), ForeignKey('countries.id', name="fk_school_country"), index=True)
    official_identifier = Column(String(512))

    Index("index_schools_by_country", country_code, official_identifier, unique=True)
    #UniqueConstraint(country_code, official_identifier, name="unique_schools")

    state = Column(Enum(SchoolState), nullable=False, default=SchoolState.ACTIVE)

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
    info = Column(JSON)

    country = relationship('Country')

    collection = relationship('CollectionItem', lazy="dynamic", cascade="all, delete")

    # https://docs.sqlalchemy.org/en/14/orm/extensions/associationproxy.html#simplifying-association-objects
    # association proxy of "collectionitems" collection
    # to "editions" attribute
    works = association_proxy('collection_items', 'work')
    editions = association_proxy('collection_items', 'edition')

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
            # Let's not allow anyone to view any school
            #(Allow, Authenticated, "read"),

            (Allow, "role:admin", "create"),
            (Allow, "role:admin", "read"),
            (Allow, "role:admin", "update"),
            (Allow, "role:admin", "delete"),
            (Allow, "role:admin", "batch"),

            (Allow, "role:lms", "batch"),
            (Allow, "role:lms", "update"),

            (Deny, "role:student", "update"),
            (Deny, "role:student", "delete"),

            (Allow, f"school:{self.id}", "read"),
            (Allow, f"school:{self.id}", "update"),
        ]
