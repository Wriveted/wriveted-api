import random
import secrets
from datetime import timedelta
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from app import crud
from app.api.dependencies.security import create_user_access_token
from app.db.session import database_connection, get_session
from app.main import app, get_settings
from app.models import School, SchoolState, ServiceAccountType, Student
from app.models.class_group import ClassGroup
from app.models.user import UserAccountType
from app.models.work import WorkType
from app.schemas.author import AuthorCreateIn
from app.schemas.service_account import ServiceAccountCreateIn
from app.schemas.users.user_create import UserCreateIn
from app.schemas.work import WorkCreateIn
from app.services.collections import reset_school_collection
from app.services.security import create_access_token
from app.tests.util.random_strings import random_lower_string


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def test_data_path():
    return Path(__file__).parent.parent / "data"


@pytest.fixture(scope="session")
def settings():
    yield get_settings()


@pytest.fixture(scope="session")
def session(settings):
    session = next(get_session(settings=settings))
    return session


@pytest.fixture(scope="session")
def session_factory(settings):
    engine, SessionMaker = database_connection(settings.SQLALCHEMY_DATABASE_URI)
    return SessionMaker


@pytest.fixture()
def backend_service_account(session):
    sa = crud.service_account.create(
        db=session,
        obj_in=ServiceAccountCreateIn(
            name="backend integration test account",
            type=ServiceAccountType.BACKEND,
        ),
    )
    yield sa

    session.delete(sa)


@pytest.fixture()
def test_user_account(session):
    user = crud.user.create(
        db=session,
        obj_in=UserCreateIn(
            name="integration test account (public)",
            email=f"{random_lower_string(6)}@test.com",
            first_name="Test",
            last_name_initial="L",
        ),
    )
    yield user
    session.delete(user)


@pytest.fixture()
def test_schooladmin_account(test_school, session):
    schooladmin = crud.user.create(
        db=session,
        obj_in=UserCreateIn(
            name="integration test account (school admin)",
            email=f"{random_lower_string(6)}@test.com",
            type=UserAccountType.SCHOOL_ADMIN,
            school_id=test_school.id,
        ),
    )
    yield schooladmin
    session.delete(schooladmin)


@pytest.fixture()
def test_wrivetedadmin_account(session):
    wrivetedadmin = crud.user.create(
        db=session,
        obj_in=UserCreateIn(
            name="integration test account (wriveted admin)",
            email=f"{random_lower_string(6)}@test.com",
            type=UserAccountType.WRIVETED,
        ),
    )
    yield wrivetedadmin
    session.delete(wrivetedadmin)


@pytest.fixture()
def backend_service_account_token(settings, backend_service_account):
    print("Generating auth token")
    access_token = create_access_token(
        subject=f"wriveted:service-account:{backend_service_account.id}",
        expires_delta=timedelta(
            minutes=settings.SERVICE_ACCOUNT_ACCESS_TOKEN_EXPIRE_MINUTES
        ),
    )
    return access_token


@pytest.fixture()
def test_user_account_token(test_user_account):
    print("Generating auth token")
    access_token = create_access_token(
        subject=f"wriveted:user-account:{test_user_account.id}",
        expires_delta=timedelta(minutes=5),
    )
    return access_token


@pytest.fixture()
def test_schooladmin_account_token(test_schooladmin_account):
    print("Generating auth token")
    access_token = create_access_token(
        subject=f"wriveted:user-account:{test_schooladmin_account.id}",
        expires_delta=timedelta(minutes=5),
    )
    return access_token


@pytest.fixture()
def test_wrivetedadmin_account_token(test_wrivetedadmin_account):
    print("Generating auth token")
    access_token = create_access_token(
        subject=f"wriveted:user-account:{test_wrivetedadmin_account.id}",
        expires_delta=timedelta(minutes=5),
    )
    return access_token


@pytest.fixture()
def backend_service_account_headers(backend_service_account_token):
    return {"Authorization": f"bearer {backend_service_account_token}"}


@pytest.fixture()
def test_user_account_headers(test_user_account_token):
    return {"Authorization": f"bearer {test_user_account_token}"}


@pytest.fixture()
def test_user_account_headers(test_user_account_token):
    return {"Authorization": f"bearer {test_user_account_token}"}


@pytest.fixture()
def test_schooladmin_account_headers(test_schooladmin_account_token):
    return {"Authorization": f"bearer {test_schooladmin_account_token}"}


@pytest.fixture()
def test_wrivetedadmin_account_headers(test_wrivetedadmin_account_token):
    return {"Authorization": f"bearer {test_wrivetedadmin_account_token}"}


@pytest.fixture()
def author_list(client, session):
    n = 10
    authors = [
        crud.author.create(
            db=session,
            obj_in={
                "first_name": random_lower_string(length=random.randint(2, 12)),
                "last_name": random_lower_string(length=random.randint(2, 12)),
            },
        )
        for _ in range(n)
    ]

    yield authors

    for a in authors:
        crud.author.remove(db=session, id=a.id)


@pytest.fixture()
def works_list(client, session, author_list):
    n = 100

    works = []
    for _ in range(n):
        author = random.choice(author_list)
        work_authors = [
            AuthorCreateIn(first_name=author.first_name, last_name=author.last_name)
        ]
        works.append(
            crud.work.get_or_create(
                db=session,
                work_data=WorkCreateIn(
                    type=WorkType.BOOK,
                    title=random_lower_string(),
                    authors=work_authors,
                ),
                authors=[author],
            )
        )

    yield works

    for w in works:
        crud.work.remove(db=session, id=w.id)


@pytest.fixture()
def test_school(client, session, backend_service_account_headers) -> School:
    # Creating a test school (we could do this directly e.g. using crud or the api)
    test_school_id = secrets.token_hex(8)

    new_test_school_response = client.post(
        "/v1/school",
        headers=backend_service_account_headers,
        json={
            "name": f"Test School - {test_school_id}",
            "country_code": "ATA",
            "official_identifier": test_school_id,
            "info": {
                "msg": "Created for test purposes",
                "location": {"state": "Required", "postcode": "Required"},
            },
        },
        timeout=120,
    )
    new_test_school_response.raise_for_status()
    school_info = new_test_school_response.json()
    # yield SchoolDetail(**school_info)

    print("Yielding from school fixture")
    # Actually lets return the orm object to the tests
    school = crud.school.get_by_wriveted_id_or_404(
        db=session, wriveted_id=school_info["wriveted_identifier"]
    )
    school.state = SchoolState.ACTIVE
    session.add(school)
    session.commit()

    school_id = school.id
    yield school
    print("Cleaning up school fixture")
    # Afterwards delete it

    session.rollback()
    if crud.school.get(session, id=school_id) is not None:
        crud.school.remove(db=session, obj_in=school)


@pytest.fixture()
def test_class_group(
    client, session, backend_service_account_headers, test_school
) -> ClassGroup:
    print("Fixture to create class group")
    new_test_class_response = client.post(
        f"/v1/school/{test_school.wriveted_identifier}/class",
        headers=backend_service_account_headers,
        json={"name": f"Test Class", "school_id": str(test_school.wriveted_identifier)},
        timeout=120,
    )
    new_test_class_response.raise_for_status()
    class_info = new_test_class_response.json()
    print("Yielding from group fixture", class_info)
    yield crud.class_group.get(db=session, id=class_info["id"])

    print("Cleaning up group fixture")
    # Afterwards delete it
    client.delete(
        f"/v1/class/{class_info['id']}",
        headers=backend_service_account_headers,
    )


@pytest.fixture()
def test_school_with_students(client, session, test_school, test_class_group) -> School:
    for i in range(100):
        student = Student(
            name=f"Test Student {i}",
            email=f"teststudent-{i}@test.com",
            type=UserAccountType.STUDENT,
            school_id=test_school.id,
            first_name=f"Test-{i}",
            last_name_initial="T",
            class_group_id=test_class_group.id,
        )
        session.add(student)
        session.flush()
    return test_school


@pytest.fixture()
def test_isbns():
    return [
        "9780007453573",
        "9780141321288",
        "9780008197049",
        "9780008355050",
        "9780734410672",
        "9780143782797",
        "9780143308591",
        "9780006754008",
    ]


@pytest.fixture()
def test_unhydrated_editions(client, session, test_isbns):
    # Create a few editions
    editions = [
        crud.edition.get_or_create_unhydrated(db=session, isbn=isbn)
        for isbn in test_isbns
    ]

    yield editions

    for e in editions:
        crud.edition.remove(db=session, id=e.isbn)


@pytest.fixture()
def test_school_with_collection(
    client, session, test_school, test_unhydrated_editions
) -> School:

    for e in test_unhydrated_editions:
        crud.collection_item.create(
            db=session,
            obj_in={"school_id": test_school.id, "edition_isbn": e.isbn},
            commit=False,
        )

    session.commit()

    assert test_school.collection_count == len(test_unhydrated_editions)

    yield test_school

    reset_school_collection(session=session, school=test_school)


@pytest.fixture()
def admin_of_test_school(session, test_school, test_schooladmin_account):
    test_schooladmin_account.school_id = test_school.id
    session.add(test_schooladmin_account)
    session.commit()
    yield test_schooladmin_account


@pytest.fixture()
def admin_of_test_school_token(admin_of_test_school):
    return create_user_access_token(admin_of_test_school)


@pytest.fixture()
def admin_of_test_school_headers(admin_of_test_school_token):
    return {"Authorization": f"bearer {admin_of_test_school_token}"}


@pytest.fixture()
def lms_service_account_for_test_school(session, test_school):
    print("Creating a LMS service account to carry out the rest of the test")
    sa = crud.service_account.create(
        db=session,
        obj_in=ServiceAccountCreateIn(
            **{
                "name": f"Integration Test Service Account - {test_school.id}",
                "type": "lms",
                "schools": [
                    {
                        "name": test_school.name,
                        "country_code": "ATA",
                        "official_identifier": test_school.id,
                        "wriveted_identifier": test_school.wriveted_identifier,
                    }
                ],
                "info": {"msg": "Created for test purposes"},
            }
        ),
    )

    yield sa

    crud.service_account.remove(db=session, id=sa.id)


@pytest.fixture()
def lms_service_account_token_for_school(settings, lms_service_account_for_test_school):
    access_token = create_access_token(
        subject=f"wriveted:service-account:{lms_service_account_for_test_school.id}",
        expires_delta=timedelta(
            minutes=settings.SERVICE_ACCOUNT_ACCESS_TOKEN_EXPIRE_MINUTES
        ),
    )
    return access_token


@pytest.fixture()
def lms_service_account_headers_for_school(lms_service_account_token_for_school):
    return {"Authorization": f"bearer {lms_service_account_token_for_school}"}
