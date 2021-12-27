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
from app.db import Base

import enum


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
    collection = relationship('CollectionItem')

    # https://docs.sqlalchemy.org/en/14/orm/extensions/associationproxy.html#simplifying-association-objects
    # association proxy of "collectionitems" collection
    # to "editions" attribute
    works = association_proxy('collection_items', 'work')
    editions = association_proxy('collection_items', 'edition')


    def __repr__(self):
        return f"<School '{self.name}' ({self.official_identifier} - {self.country.name})>"
