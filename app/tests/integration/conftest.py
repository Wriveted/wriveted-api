import os
import random
import secrets
import time
import logging
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from starlette.testclient import TestClient

# Set up verbose logging for debugging test setup failures
logger = logging.getLogger(__name__)

from app import crud
from app.api.dependencies.security import create_user_access_token
from app.db.session import (
    database_connection,
    get_async_session_maker,
    get_session_maker,
)
from app.main import app, get_settings
from app.models import Collection, School, SchoolState, ServiceAccountType, Student
from app.models.class_group import ClassGroup
from app.models.user import UserAccountType
from app.models.work import WorkType
from app.schemas.author import AuthorCreateIn
from app.schemas.collection import (
    CollectionAndItemsUpdateIn,
    CollectionCreateIn,
    CollectionItemCreateIn,
    CollectionItemUpdate,
    CollectionUpdateType,
)
from app.schemas.edition import EditionCreateIn
from app.schemas.product import ProductCreateIn
from app.schemas.recommendations import HueKeys, ReadingAbilityKey
from app.schemas.service_account import ServiceAccountCreateIn
from app.schemas.users.huey_attributes import HueyAttributes
from app.schemas.users.user_create import UserCreateIn
from app.schemas.work import WorkCreateIn
from app.services.collections import reset_collection
from app.services.editions import generate_random_valid_isbn13
from app.services.security import create_access_token
from app.tests.util.random_strings import random_lower_string


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        # This is because we want to keep debugging tests for longer but the agent
        # has a rate limit.
        # Only sleep if explicitly requested via environment variable
        if os.getenv("TEST_DEBUG_SLEEP") == "true":
            time.sleep(60)

        yield c


@pytest.fixture(
    scope="session",
    params=[
        pytest.param(("asyncio", {"use_uvloop": True}), id="asyncio+uvloop"),
    ],
)
def anyio_backend(request):
    return request.param


@pytest.fixture(scope="module")
def test_data_path():
    return Path(__file__).parent.parent / "data"


@pytest.fixture(scope="session")
def settings():
    yield get_settings()


@pytest.fixture(scope="session")
def test_app() -> FastAPI:
    """Create a test app with overridden dependencies."""
    # app.dependency_overrides[get_db_session] = lambda: db_session

    return app


@pytest.fixture
async def async_client(test_app):
    from httpx import ASGITransport

    logger.debug("Creating async HTTP client for testing")

    try:
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            logger.debug("Successfully created async client")
            yield client
            logger.debug("Async client context manager exiting")
    except Exception as e:
        logger.error(f"Error creating async client: {e}")
        raise


@pytest.fixture
async def internal_async_client():
    """AsyncClient for the internal API."""
    from httpx import ASGITransport

    from app.internal_api import internal_app

    async with AsyncClient(
        transport=ASGITransport(app=internal_app), base_url="http://test"
    ) as client:
        yield client


@pytest.fixture()
def session(settings):
    """Create a clean database session for each test with proper cleanup."""
    session_maker = get_session_maker()
    session = session_maker()
    try:
        yield session
    finally:
        # Ensure proper cleanup - rollback any uncommitted changes
        try:
            session.rollback()
        except Exception:
            pass
        finally:
            session.close()


@pytest.fixture()
async def async_session():
    """Create an isolated async session for each test with proper cleanup."""
    logger.debug("Creating async session for test")

    try:
        session_factory = get_async_session_maker()
        logger.debug("Got async session factory")

        session = session_factory()
        logger.debug(f"Created async session: {session}")

        # Test session connectivity
        try:
            from sqlalchemy import text

            result = await session.execute(text("SELECT 1"))
            logger.debug("Session connectivity test successful")
        except Exception as e:
            logger.error(f"Session connectivity test failed: {e}")
            raise

        yield session
        logger.debug("Test completed, starting session cleanup")

    except Exception as e:
        logger.error(f"Error creating async session: {e}")
        raise
    finally:
        # Ensure proper cleanup
        try:
            # Rollback any uncommitted transactions
            if session.in_transaction():
                logger.debug("Rolling back uncommitted transactions")
                await session.rollback()
        except Exception as e:
            logger.warning(f"Error during session rollback: {e}")
        finally:
            # Always close the session
            try:
                logger.debug("Closing async session")
                await session.close()
            except Exception as e:
                logger.warning(f"Error closing session: {e}")


@pytest.fixture()
def session_factory(settings):
    """Create session factory for each test with proper engine management."""
    engine, SessionMaker = database_connection(settings.SQLALCHEMY_DATABASE_URI)
    try:
        yield SessionMaker
    finally:
        # Clean up engine connections
        try:
            engine.dispose()
        except Exception:
            pass


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

    try:
        session.delete(sa)
        session.commit()
    except Exception:
        session.rollback()


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
    try:
        session.delete(user)
        session.commit()
    except Exception:
        session.rollback()


@pytest.fixture()
def test_student_user_account(session, test_school, test_class_group):
    student = crud.user.create(
        db=session,
        obj_in=UserCreateIn(
            name="integration test account (student)",
            email=f"{random_lower_string(6)}@test.com",
            first_name="Test",
            last_name_initial="A",
            type="student",
            school_id=test_school.id,
            class_group_id=test_class_group.id,
            username=random_lower_string(6),
        ),
    )
    yield student
    try:
        session.delete(student)
        session.commit()
    except Exception:
        session.rollback()


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
    try:
        session.delete(schooladmin)
        session.commit()
    except Exception:
        session.rollback()


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
    try:
        session.delete(wrivetedadmin)
        session.commit()
    except Exception:
        session.rollback()


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
def test_student_user_account_token(test_student_user_account):
    print("Generating auth token")
    access_token = create_access_token(
        subject=f"wriveted:user-account:{test_student_user_account.id}",
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
def test_student_user_account_headers(test_student_user_account_token):
    return {"Authorization": f"bearer {test_student_user_account_token}"}


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

    try:
        for a in authors:
            crud.author.remove(db=session, id=a.id)
        session.commit()
    except Exception:
        session.rollback()


@pytest.fixture()
def test_product(session):
    product = crud.product.get(db=session, id="integration-test-product")
    if not product:
        product = crud.product.create(
            db=session,
            obj_in=ProductCreateIn(
                name="Super Cool Tier",
                id="integration-test-product",
            ),
        )
    yield product
    try:
        session.delete(product)
        session.commit()
    except Exception:
        session.rollback()


@pytest.fixture()
def works_list(client, session, author_list):
    n = 100

    works = []
    for _ in range(n):
        author = random.choice(author_list)
        work_authors = [
            AuthorCreateIn(first_name=author.first_name, last_name=author.last_name)
        ]
        work = crud.work.get_or_create(
            db=session,
            work_data=WorkCreateIn(
                type=WorkType.BOOK,
                title=random_lower_string(),
                authors=work_authors,
            ),
            authors=[author],
        )
        crud.edition.create(
            db=session,
            edition_data=EditionCreateIn(
                isbn=generate_random_valid_isbn13(),
                title=random_lower_string(length=random.randint(2, 12)),
                cover_url="https://cool.site",
                info={},
            ),
            work=work,
            illustrators=[],
        )

        works.append(work)

    yield works

    try:
        for w in works:
            crud.work.remove(db=session, id=w.id)
        session.commit()
    except Exception:
        session.rollback()


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
        json={"name": "Test Class", "school_id": str(test_school.wriveted_identifier)},
        timeout=120,
    )
    print(new_test_class_response.status_code)
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

    try:
        for e in editions:
            crud.edition.remove(db=session, id=e.isbn)
        session.commit()
    except Exception:
        session.rollback()


@pytest.fixture()
def test_user_empty_collection(
    client,
    session,
    test_user_account,
    test_user_account_headers,
) -> Collection:
    collection, created = crud.collection.get_or_create(
        db=session,
        collection_data=CollectionCreateIn(
            name=f"Test Collection {random_lower_string(length=8)}",
            user_id=test_user_account.id,
            info={"msg": "Created for test purposes"},
        ),
    )
    yield collection
    try:
        crud.collection.remove(db=session, id=collection.id)
        session.commit()
    except Exception:
        session.rollback()


@pytest.fixture()
def test_user_collection(
    client, session, test_user_empty_collection: Collection, test_unhydrated_editions
):
    # Add items to existing collection
    for edition in test_unhydrated_editions:
        crud.collection.add_item_to_collection(
            session,
            collection_orm_object=test_user_empty_collection,
            item=CollectionItemCreateIn(edition_isbn=edition.isbn),
            commit=False,
        )
    session.commit()
    yield test_user_empty_collection


@pytest.fixture()
def test_school_with_collection(
    client,
    session,
    test_school: School,
    test_unhydrated_editions,
    backend_service_account,
) -> School:
    collection, created = crud.collection.get_or_create(
        db=session,
        collection_data=CollectionCreateIn(
            name=f"Books at {test_school.name}",
            school_id=test_school.wriveted_identifier,
            info={"msg": "Created for test purposes"},
        ),
    )

    items = [
        CollectionItemUpdate(edition_isbn=e.isbn, action=CollectionUpdateType.ADD)
        for e in test_unhydrated_editions
    ]

    crud.collection.update(
        db=session, db_obj=collection, obj_in=CollectionAndItemsUpdateIn(items=items)
    )
    session.commit()

    collection: Collection = test_school.collection
    assert collection.book_count == len(test_unhydrated_editions)

    yield test_school

    reset_collection(
        session=session, collection=collection, account=backend_service_account
    )


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

    try:
        crud.service_account.remove(db=session, id=sa.id)
        session.commit()
    except Exception:
        session.rollback()


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


@pytest.fixture()
def test_public_user_hacker(session):
    hacker = crud.user.create(
        db=session,
        obj_in=UserCreateIn(
            name="NotAHacker", email=f"{random_lower_string(6)}@notahacker.com"
        ),
    )
    yield hacker
    try:
        session.delete(hacker)
        session.commit()
    except Exception:
        session.rollback()


@pytest.fixture()
def test_public_user_hacker_token(test_public_user_hacker):
    return create_user_access_token(test_public_user_hacker)


@pytest.fixture()
def test_public_user_hacker_headers(test_public_user_hacker_token):
    return {"Authorization": f"bearer {test_public_user_hacker_token}"}


@pytest.fixture()
def test_huey_attributes():
    return HueyAttributes(
        birthdate="2015-01-01 00:00:00",
        last_visited="2022-05-05 00:00:00",
        age=7,
        reading_ability=[ReadingAbilityKey.CAT_HAT],
        hues=[HueKeys.hue01_dark_suspense, HueKeys.hue03_dark_beautiful],
        goals=["Maintain a thoroughly-tested codebase"],
        genres=["Dark", "Realistic"],
        characters=["Robot", "Unicorn"],
    )


@pytest.fixture(autouse=True)
def clear_test_client_cookies(client):
    """Ensure test isolation by clearing TestClient cookies between tests.
    
    This fixes CSRF token conflicts when chat API tests run together.
    Each test gets a fresh cookie jar to prevent token interference.
    """
    # Clear all cookies before test runs
    client.cookies.clear()
    yield
    # Clear cookies after test completes for good measure
    client.cookies.clear()
