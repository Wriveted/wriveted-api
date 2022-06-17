import pytest
from sqlalchemy import select

from app import crud
from app.models import PublicReader, SchoolAdmin, Student, WrivetedAdmin
from app.models.reader import Reader
from app.models.user import UserAccountType
from app.schemas.users.user_create import UserCreateIn
from app.schemas.users.user_update import UserUpdateIn
from app.tests.util.random_strings import random_lower_string


def test_user_crud_extracts_name_components(session, test_school):
    publicuser = crud.user.create(
        db=session,
        obj_in=UserCreateIn(
            name="Test User",
            email=f"{random_lower_string(6)}@test.com",
            # first_name="Test",
            # last_name_initial="U",
        ),
        commit=False,
    )
    assert isinstance(
        publicuser, PublicReader
    ), "CRUD: User account without specified type not constructing a PublicReader object"

    assert publicuser.first_name == "Test"
    assert publicuser.last_name_initial == "U"


def test_user_crud_types(session, test_school, test_class_group):
    test_email = f"{random_lower_string(6)}@test.com"
    publicuser = crud.user.create(
        db=session,
        obj_in=UserCreateIn(
            name="integration test account (user)",
            email=test_email,
            first_name="Test",
            last_name_initial="T",
        ),
        commit=True,
    )
    assert isinstance(
        publicuser, PublicReader
    ), "CRUD: User account without specified type not constructing a PublicReader object"
    retrieved_public_user = crud.user.get_by_account_email(session, test_email)
    assert retrieved_public_user is not None, "couldn't retrieve public user by email"
    assert retrieved_public_user.id == publicuser.id
    deleted_public_user = crud.user.remove(session, id=publicuser.id)
    assert deleted_public_user.type == UserAccountType.PUBLIC

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
    deleted_wriveted_user = crud.user.remove(session, id=wrivetedadmin.id)

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
    deleted_school_admin = crud.user.remove(session, id=schooladmin.id)
    student = crud.user.create(
        db=session,
        obj_in=UserCreateIn(
            email=f"{random_lower_string(6)}@test.com",
            type=UserAccountType.STUDENT,
            first_name="Test",
            last_name_initial="S",
            school_id=test_school.id,
            class_group_id=test_class_group.id,
        ),
        commit=False,
    )
    assert isinstance(
        student, Student
    ), "CRUD: User account with type='student' not constructing a Student object"

    assert student.name == "Test S"
    assert student.first_name == "Test"
    assert student.last_name_initial == "S"

    crud.user.remove(session, id=student.id)


def test_cross_model_updates(session, test_school, test_class_group):
    fake_domain = random_lower_string(12)
    student = crud.user.create(
        db=session,
        obj_in=UserCreateIn(
            email=f"teststudentupdate5@{fake_domain}.com",
            type=UserAccountType.STUDENT,
            school_id=test_school.id,
            first_name="Joe Shooer",
            last_name_initial="P",
            class_group_id=test_class_group.id,
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


def test_access_subclass_through_superclass_query(
    session, test_school, test_class_group
):

    student = crud.user.create(
        db=session,
        obj_in=UserCreateIn(
            name="Test Student to retrieve via parent tables",
            email=f"teststudentretrieve@test.com",
            type=UserAccountType.STUDENT,
            school_id=test_school.id,
            first_name="Test",
            last_name_initial="T",
            class_group_id=test_class_group.id,
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


def test_user_info_dict_merging(
    session
):
    original_reading_preferences = {
        "last_visited": "now"
    }
    updated_reading_preferences = {
        "reading_ability": "yeah not bad"
    }

    reader = crud.user.create(
        db=session,
        obj_in=UserCreateIn(
            name="Test Reader to update reading preferences",
            email=f"testreaderupdatemerge3@test.com",
            type=UserAccountType.PUBLIC,
            first_name="Test",
            last_name_initial="T",
            reading_preferences=original_reading_preferences
        ),
        commit=False,
    )
    session.add(reader)
    session.flush()
    assert reader.id

    updated_reader_without_merge = crud.user.update(db=session, obj_in=UserUpdateIn(reading_preferences=updated_reading_preferences), db_obj=reader, merge_dicts=False)
    assert updated_reader_without_merge.reading_preferences['reading_ability']
    with pytest.raises(KeyError):
        updated_reader_without_merge.reading_preferences['last_visited']

    updated_reader_with_merge = crud.user.update(db=session, obj_in=UserUpdateIn(reading_preferences=original_reading_preferences), db_obj=reader, merge_dicts=True)
    assert updated_reader_with_merge.reading_preferences['reading_ability']
    assert updated_reader_with_merge.reading_preferences['last_visited']

    session.rollback()