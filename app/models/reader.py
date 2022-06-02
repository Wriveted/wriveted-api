from sqlalchemy import (
    JSON,
    Column,
    ForeignKey,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship

from app.models.user import User
from app.services.users import new_identifiable_username

def contextual_default_username_generation(context):
    first_name = context.get_current_parameters()['first_name']
    last_name_initial = context.get_current_parameters()['last_name_initial']
    return new_identifiable_username(first_name, last_name_initial)


class Reader(User):
    """
    An abstract user of Huey for reading purposes.
    Note: only functionally abstract (has db tables for ORM purposes, but no meaningful instantiation).
    """

    id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_reader_inherits_user"),
        primary_key=True,
    )

    username = Column(String, unique=True, index=True, nullable=False, default=contextual_default_username_generation)
    first_name = Column(String, nullable=False)
    last_name_initial = Column(String, nullable=False)

    parent_id = Column(
        UUID,
        ForeignKey("parents.id", name="fk_reader_parent"),
        nullable=True,
        index=True,
    )
    parent = relationship("Parent", backref="children", foreign_keys=[parent_id])

    # reading_ability, age, last_visited, etc
    reading_preferences = Column(
        MutableDict.as_mutable(JSON), nullable=True, default={}
    )
