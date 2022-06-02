from app import crud
from app.models import WrivetedAdmin, SchoolAdmin, Student, User, PublicReader
from app.models.user import UserAccountType
from app.schemas.user import UserCreateIn, UserUpdateIn
from app.tests.util.random_strings import random_lower_string


def test_user_crud_types(session):
    publicuser = crud.user.create(
        db=session,
        obj_in=UserCreateIn(
            name="integration test account (user)",
            email=f"{random_lower_string(6)}@test.com"
        ),
        commit=False,
    )
    assert isinstance(
        publicuser, PublicReader
    ), "CRUD: User account without specified type not constructing a PublicReader object"

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
            type=UserAccountType.SCHOOL_ADMIN,
        ),
        commit=False,
    )
    assert isinstance(
        schooladmin, SchoolAdmin
    ), "CRUD: User account with type='SCHOOL_ADMIN' not constructing a SchoolAdmin object"

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


def test_cross_model_updates(session, test_school):
    
    student = crud.user.create(
        db=session,
        obj_in=UserCreateIn(
            name="Test Student to Update",
            email=f"teststudentupdate@test.com",
            type=UserAccountType.STUDENT,
            school_id=test_school.id,
            first_name="Test",
            last_name_initial="T"
        ),
        commit=True,
    )

    update = UserUpdateIn(first_name="Joshua", last_name_initial="L")

    updated_student = crud.user.update(db=session, obj_in=update, db_obj=student)
    assert (
        updated_student.first_name == "Joshua"
        and updated_student.last_name_initial == "L"
        and isinstance(updated_student, Student)
    )

    