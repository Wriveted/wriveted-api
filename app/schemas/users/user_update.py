from __future__ import annotations

from uuid import UUID

from pydantic import UUID4, BaseModel, EmailStr, model_validator

from app.models.user import UserAccountType
from app.schemas.users.huey_attributes import HueyAttributes
from app.schemas.users.user import UserInfo

user_base_attributes = ["name"]
reader_attributes = user_base_attributes + ["first_name", "last_name_initial"]
student_attributes = reader_attributes + ["school_id", "class_group_id", "username"]
educator_attributes = user_base_attributes + ["school_id"]
school_admin_attributes = educator_attributes + []
parent_attributes = user_base_attributes + []
wriveted_attributes = user_base_attributes + []

user_type_attributes_map = {
    UserAccountType.PUBLIC: reader_attributes,
    UserAccountType.STUDENT: student_attributes,
    UserAccountType.EDUCATOR: educator_attributes,
    UserAccountType.SCHOOL_ADMIN: school_admin_attributes,
    UserAccountType.PARENT: parent_attributes,
    UserAccountType.WRIVETED: wriveted_attributes,
}


class UserUpdateIn(BaseModel):
    # all users
    name: str | None = None
    is_active: bool | None = None
    email: EmailStr | None = None
    info: UserInfo | None = None
    newsletter: bool | None = None

    # readers
    first_name: str | None = None
    last_name_initial: str | None = None
    huey_attributes: HueyAttributes | None = None

    # students
    username: str | None = None

    # students + educators
    school_id: UUID | None = None
    class_group_id: UUID | None = None

    # changing user type
    type: UserAccountType | None = None


class InternalUserUpdateIn(UserUpdateIn):
    current_type: UserAccountType | None = None
    school_id: UUID4 | int | None = None

    @model_validator(mode="after")
    def validate_user_creation(self):
        new_type: UserAccountType = self.type
        current_type: UserAccountType = self.current_type

        if new_type:
            # if changing types, ensure the required fields of new_type are met
            # by the union of the current_type's fields and provided UserUpdateIn fields
            update_attributes = [k for k, v in dict(self).items() if v is not None]
            existing_attributes = user_type_attributes_map[current_type]
            current_attributes = update_attributes + existing_attributes

            needed_attributes = user_type_attributes_map[new_type]

            difference = set(needed_attributes) - set(current_attributes)
            assert not difference, (
                f"Missing attributes: {difference}"
                f"Not all required attributes have been provided to change from user type '{current_type.value}' to '{new_type.value}'. "
                f"Missing attributes: {[a for a in needed_attributes if a not in current_attributes]}."
            )
