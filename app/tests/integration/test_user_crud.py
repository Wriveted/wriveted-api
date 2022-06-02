from sqlalchemy import select
from app import crud
from app.models import WrivetedAdmin, SchoolAdmin, Student, User, PublicReader
from app.models.reader import Reader
from app.models.user import UserAccountType
from app.schemas.user import UserCreateIn, UserUpdateIn
from app.tests.util.random_strings import random_lower_string


def test_user_crud_types(session, test_school):
    publicuser = crud.user.create(
        db=session,
        obj_in=UserCreateIn(
            name="integration test account (user)",
            email=f"{random_lower_string(6)}@test.com",
            first_name="Test",
            last_name_initial="T",
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
            school_id=test_school.id,
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
            first_name="Test",
            last_name_initial="S",
            school_id=test_school.id,
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
            email=f"teststudentupdate5@test.com",
            type=UserAccountType.STUDENT,
            school_id=test_school.id,
            first_name="Joshua",
            last_name_initial="L",
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


def test_access_subclass_through_superclass_query(session, test_school):

    student = crud.user.create(
        db=session,
        obj_in=UserCreateIn(
            name="Test Student to retrieve via parent tables",
            email=f"teststudentretrieve@test.com",
            type=UserAccountType.STUDENT,
            school_id=test_school.id,
            first_name="Test",
            last_name_initial="T",
        ),
        commit=False,
    )
    session.add(student)
    session.flush()

    assert student.id

    assert (
        crud.user.get_by_account_email(session, "teststudentretrieve@test.com")
        is not None
    )

    reader = session.execute(
        select(Reader).where(Reader.email == "teststudentretrieve@test.com")
    ).scalar_one_or_none()

    assert reader == student

    session.rollback()
