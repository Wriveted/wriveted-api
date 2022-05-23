from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    UniqueConstraint,
    func,
)
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship

from app.db import Base
from app.models.user_group import GroupType


class UserGroupMembership(Base):

    __tablename__ = "user_group_memberships"

    user_group_id = Column(
        ForeignKey(
            "user_groups.id",
            name="fk_user_group_memberships_user_group_id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    # duplicate reference to the group type so we can add constraints if desired
    # (without relying on triggers from the user_groups table)
    group_type = Column(
        Enum(GroupType, name="enum_user_group_type"), nullable=False, index=True
    )

    user_id = Column(
        ForeignKey(
            "users.id", name="fk_user_group_memberships_user_id", ondelete="CASCADE"
        ),
        primary_key=True,
    )

    Index("index_users_per_group", user_id, user_group_id, unique=True)

    created_at = Column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    info = Column(MutableDict.as_mutable(JSON))

    user_group = relationship("UserGroup", back_populates="users")
    user = relationship("User", lazy="joined", viewonly=True)

    def __repr__(self):
        try:
            return f"<UserGroupMembership '{self.user}' @ '{self.user_group}'>"
        except AttributeError:
            return f"<UserGroupMemberhsip work_id={self.work_id}>"
