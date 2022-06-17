from __future__ import annotations

from pydantic import UUID4, BaseModel, EmailStr, root_validator, validator

from app.models.user import UserAccountType
from app.schemas.users.reading_preferences import ReadingPreferences
from app.schemas.users.user import UserInfo


class UserCreateAuth(BaseModel):
    """
    A schema to validate any initial `/auth/me` call that creates a user.
    """

    type: UserAccountType | None = UserAccountType.PUBLIC
    username: str | None
    first_name: str | None
    last_name_initial: str | None
    school_id: UUID4 | None
    class_join_code: UUID4 | None

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
    name: str | None
    email: EmailStr | None
    info: UserInfo | None
    type: UserAccountType | None = UserAccountType.PUBLIC

    # readers
    username: str | None
    first_name: str | None
    last_name_initial: str | None
    reading_preferences: ReadingPreferences | None = {}

    # students / educators
    school_id: int | None
    class_group_id: UUID4 | None

    student_info: dict | None
    school_admin_info: dict | None
    wriveted_admin_info: dict | None

    @validator("first_name", always=True)
    def extract_first_name(cls, v, values, **kwargs):
        if (
            v is None
            and "name" in values
            and "type" in values
            and values["type"] in {"public", "student"}
        ):
            # Extract first name from name
            return values["name"].split()[0]
        else:
            return v

    @validator("last_name_initial", always=True)
    def extract_last_name_initial(cls, v, values, **kwargs):
        if (
            v is None
            and "name" in values
            and "type" in values
            and values["type"] in {"public", "student"}
        ):
            # Extract last name initial from name
            return values["name"].split()[-1][0]
        else:
            return v

    @root_validator
    def validate_user_creation(cls, values):
        match values["type"]:
            case UserAccountType.STUDENT:
                if not (
                    values["first_name"]
                    and values["last_name_initial"]
                    and values["school_id"]
                    and values["class_group_id"]
                ):
                    raise ValueError(
                        "Student users must provide first_name, last_name_initial, school_id, and class_group_id."
                    )
                else:
                    values[
                        "name"
                    ] = f"{values['first_name']} {values['last_name_initial']}"
            case UserAccountType.EDUCATOR:
                if not (
                    values["first_name"]
                    and values["last_name_initial"]
                    and values["school_id"]
                ):
                    raise ValueError("Educator users must provide school_id.")
            case UserAccountType.SCHOOL_ADMIN:
                if not (values["school_id"]):
                    raise ValueError("SchoolAdmin users must provide school_id.")
            case _:
                pass

        return values
