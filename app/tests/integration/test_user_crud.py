from app import crud
from app.models import WrivetedAdmin, SchoolAdmin, Student, User
from app.models.user import UserAccountType
from app.schemas.user import UserCreateIn, UserUpdateIn
from app.tests.util.random_strings import random_lower_string


def test_user_crud_types(session):
    publicuser = crud.user.create(
        db=session,
        obj_in=UserCreateIn(
            name="integration test account (user)",
            email=f"{random_lower_string(6)}@test.com",
            type=UserAccountType.PUBLIC,
        ),
        commit=False,
    )
    assert isinstance(
        publicuser, User
    ), "CRUD: User account with type='public' not constructing a User object"

    wrivetedadmin = crud.user.create(
        db=session,
        obj_in=UserCreateIn(
            name="integration test account (wriveted admin)",
            email=f"{random_lower_string(6)}@test.com",
            type=UserAccountType.WRIVETED,
        ),
        commit=False,
    )
    assert isinstance(
        wrivetedadmin, WrivetedAdmin
    ), "CRUD: User account with type='wriveted' not constructing a WrivetedAdmin object"

    schooladmin = crud.user.create(
        db=session,
        obj_in=UserCreateIn(
            name="integration test account (school admin)",
            email=f"{random_lower_string(6)}@test.com",
            type=UserAccountType.LIBRARY,
        ),
        commit=False,
    )
    assert isinstance(
        schooladmin, SchoolAdmin
    ), "CRUD: User account with type='library' not constructing a SchoolAdmin object"

    student = crud.user.create(
        db=session,
        obj_in=UserCreateIn(
            name="integration test account (student)",
            email=f"{random_lower_string(6)}@test.com",
            type=UserAccountType.STUDENT,
        ),
        commit=False,
    )
    assert isinstance(
        student, Student
    ), "CRUD: User account with type='student' not constructing a Student object"


def test_cross_model_updates(session):
    student = crud.user.create(
        db=session,
        obj_in=UserCreateIn(
            name="Test Student to Update",
            email=f"{random_lower_string(6)}@test.com",
            type=UserAccountType.STUDENT,
        ),
        commit=False,
    )

    update = UserUpdateIn(
        first_name="Joshua",
        last_name_initial="L"
    )
   
    updated_student = crud.user.update(
        db=session,
        obj_in=update,
        db_obj=student
    )
    assert updated_student.first_name == "Joshua" and updated_student.last_name_initial == "L"