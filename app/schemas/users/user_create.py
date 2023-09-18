from __future__ import annotations

from pydantic import UUID4, BaseModel, EmailStr, root_validator

from app.models.user import UserAccountType
from app.schemas.users.huey_attributes import HueyAttributes
from app.schemas.users.user import UserInfo


class UserCreateAuth(BaseModel):
    """
    A schema to validate any initial `/auth/me` call that creates a user.
    """

    type: UserAccountType | None = UserAccountType.PUBLIC
    username: str | None = None
    first_name: str | None = None
    last_name_initial: str | None = None
    school_id: UUID4 | None = None
    class_join_code: UUID4 | None = None

    @root_validator
    def validate_user_creation(cls, values):
        match values.get("type"):
            case UserAccountType.STUDENT:
                if not (values.get("school_id") and values.get("class_join_code")):
                    raise ValueError(
                        "Student users must provide school_id and class_join_code."
                    )
                else:
                    values[
                        "name"
                    ] = f"{values['first_name']} {values['last_name_initial']}"
            case UserAccountType.EDUCATOR:
                if not (
                    values.get("first_name")
                    and values.get("last_name_initial")
                    and values.get("school_id")
                ):
                    raise ValueError("Educator users must provide school_id.")
            case UserAccountType.SCHOOL_ADMIN:
                if not (values.get("school_id")):
                    raise ValueError("SchoolAdmin users must provide school_id.")
            case _:
                pass

        return values


class UserCreateIn(BaseModel):
    # all users
    name: str = None
    email: EmailStr | None = None
    info: UserInfo | None = None
    type: UserAccountType = UserAccountType.PUBLIC
    newsletter: bool = False

    # readers
    username: str | None = None
    first_name: str | None = None
    last_name_initial: str | None = None
    huey_attributes: HueyAttributes | None = None
    parent_id: UUID4 | None = None

    # students / educators
    school_id: UUID4 | int | None = None
    class_group_id: UUID4 | None = None

    # parents
    children: list[UserCreateIn] | None = None

    # subscription
    checkout_session_id: str | None = None

    @root_validator
    def validate_user_creation(cls, values):
        # infer names from other fields if necessary
        name = values.get("name")
        first_name = values.get("first_name")
        last_name_initial = values.get("last_name_initial")

        # Extract name from first name and initial
        if name is None and first_name and last_name_initial:
            values["name"] = f"{first_name} {last_name_initial}"

        # Extract first name and initial from name
        if name and "type" in values and values["type"] in {"public", "student"}:
            if not first_name:
                values["first_name"] = name.split()[0]
            if not last_name_initial:
                values["last_name_initial"] = name.split()[-1][0]

        # validate logic for supplied values vs. type
        match values["type"]:
            # case UserAccountType.PUBLIC:
            #     if not (values.get("first_name") and values.get("last_name_initial")):
            #         raise ValueError(
            #             "Public Readers must provide first_name and last_name_initial"
            #         )
            case UserAccountType.STUDENT:
                if not (
                    values.get("first_name")
                    and values.get("last_name_initial")
                    and values.get("school_id")
                    and values.get("class_group_id")
                ):
                    raise ValueError(
                        "Student users must provide first_name, last_name_initial, school_id, and class_group_id."
                    )
            case UserAccountType.EDUCATOR:
                if not (
                    values.get("first_name")
                    and values.get("last_name_initial")
                    and values.get("school_id")
                ):
                    raise ValueError("Educator users must provide school_id.")
            case UserAccountType.SCHOOL_ADMIN:
                if not values.get("school_id"):
                    raise ValueError("SchoolAdmin users must provide school_id.")
            case _:
                pass

        return values
