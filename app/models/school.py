from sqlalchemy import (
    Column,
    Computed,
    ForeignKey,
    Integer,
    String,
    JSON,
    Enum
)
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import relationship
from app.db import Base

import enum


class SchoolState(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class School(Base):

    id = Column(String(36), primary_key=True, nullable=False)
    state = Column(Enum(SchoolState), nullable=False, default=SchoolState.ACTIVE)

    name = Column(String(100), nullable=False)

    info = Column(JSON)

    collection = relationship('CollectionItem')

    # https://docs.sqlalchemy.org/en/14/orm/extensions/associationproxy.html#simplifying-association-objects
    # association proxy of "collectionitems" collection
    # to "editions" attribute
    works = association_proxy('collection_items', 'work')
    editions = association_proxy('collection_items', 'edition')