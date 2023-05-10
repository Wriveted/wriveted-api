from __future__ import annotations

from uuid import UUID

from pydantic import UUID4, BaseModel, EmailStr, root_validator

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
    name: str | None
    is_active: bool | None
    email: EmailStr | None
    info: UserInfo | None
    newsletter: bool | None

    # readers
    first_name: str | None
    last_name_initial: str | None
    huey_attributes: HueyAttributes | None

    # students
    username: str | None

    # students + educators
    school_id: UUID | None
    class_group_id: UUID | None

    # changing user type
    type: UserAccountType | None


class InternalUserUpdateIn(UserUpdateIn):
    current_type: UserAccountType | None
    school_id: UUID4 | int | None

    @root_validator
    def validate_user_type_change(cls, values):
        new_type: UserAccountType = values.get("type")
        current_type: UserAccountType = values.get("current_type")

        if new_type:
            # if changing types, ensure the required fields of new_type are met
            # by the union of the current_type's fields and provided UserUpdateIn fields
            update_attributes = [k for k, v in dict(values).items() if v is not None]
            existing_attributes = user_type_attributes_map[current_type]
            current_attributes = update_attributes + existing_attributes

            needed_attributes = user_type_attributes_map[new_type]

            difference = set(needed_attributes) - set(current_attributes)
            if difference:
                raise ValueError(
                    f"Not all required attributes have been provided to change from user type '{current_type.value}' to '{new_type.value}'. "
                    + f"Missing attributes: {[a for a in needed_attributes if a not in current_attributes]}."
                )

        return values
