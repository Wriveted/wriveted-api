from app import crud
from app.models import Student
from app.models.user import UserAccountType
from app.repositories.school_repository import school_repository
from app.schemas.users.user_create import UserCreateIn
from app.tests.util.random_strings import random_lower_string


def test_get_school_with_no_students(session, test_school, test_class_group):
    # session.flush()
    school = school_repository.get_by_wriveted_id_or_404(
        db=session, wriveted_id=str(test_school.wriveted_identifier)
    )
    assert school.id == test_school.id
    assert len(school.class_groups) == 1
    assert len(school.students) == 0


def test_remove_school_with_students(session_factory, test_school, test_class_group):
    # Add some Student users to a school, check the data is present, then clean it up
    with session_factory() as session:
        print("Adding students")
        fake_domain = random_lower_string(12)
        created_user_ids = []
        for i in range(10):
            user = crud.user.create(
                db=session,
                obj_in=UserCreateIn(
                    first_name=f"Test{i}",
                    last_name_initial="U",
                    email=f"test-student-{i}@test-{fake_domain}.com",
                    type=UserAccountType.STUDENT,
                    school_id=test_school.id,
                    class_group_id=test_class_group.id,
                ),
                commit=True,
            )
            created_user_ids.append(user.id)

        print("Students added to school")

        school = school_repository.get_by_wriveted_id_or_404(
            db=session, wriveted_id=str(test_school.wriveted_identifier)
        )
        print(school)
        assert school.id == test_school.id
        assert len(school.class_groups) == 1
        assert len(list(school.students)) == 10
        assert isinstance(school.students[0], Student)

        print("Removing school")
        school_repository.remove(db=session, obj_in=school)
        session.commit()
        session.close()

    with session_factory() as session:
        # Note the students are still valid users - just no longer "Students"
        u = crud.user.get_by_account_email(
            db=session, email=f"test-student-0@test-{fake_domain}.com"
        )
        assert u is not None
        assert u.type == UserAccountType.PUBLIC
