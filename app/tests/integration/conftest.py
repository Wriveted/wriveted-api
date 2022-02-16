import secrets
from datetime import timedelta

import pytest
from starlette.testclient import TestClient

from app.db.session import get_session
from app import crud
from app.main import app, get_settings
from app.models import School, ServiceAccountType
from app.schemas.school import SchoolDetail
from app.schemas.service_account import ServiceAccountCreateIn
from app.services.security import create_access_token


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def settings():
    yield get_settings()


@pytest.fixture()
def session(settings):
    session = next(get_session(settings=settings))
    return session


@pytest.fixture()
def backend_service_account(session):
    sa = crud.service_account.create(db=session, obj_in=ServiceAccountCreateIn(
        name="backend integration test account",
        type=ServiceAccountType.BACKEND,

    ))
    yield sa

    session.delete(sa)


@pytest.fixture()
def backend_service_account_token(settings, backend_service_account):
    print("Generating auth token")
    access_token = create_access_token(
        subject=f"wriveted:service-account:{backend_service_account.id}",
        expires_delta=timedelta(
            minutes=settings.SERVICE_ACCOUNT_ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )

    return access_token

@pytest.fixture()
def backend_service_account_headers(backend_service_account_token):
    return {
        "Authorization": f"bearer {backend_service_account_token}"
    }


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
                "location": {
                    "state": "Required",
                    "postcode": "Required"
                }
            }
        },
        timeout=120
    )
    print(new_test_school_response.text)
    new_test_school_response.raise_for_status()
    school_info = new_test_school_response.json()
    #yield SchoolDetail(**school_info)

    # Actually lets return the orm object to the tests
    yield crud.school.get_by_wriveted_id_or_404(db=session, wriveted_id=school_info['wriveted_identifier'])

    # Afterwards delete it
    new_test_school_response = client.delete(
        f"/v1/school/{school_info['wriveted_identifier']}",
        headers=backend_service_account_headers
    )


@pytest.fixture()
def service_account_for_test_school(client, session, test_school, backend_service_account_headers):
    print("Creating a LMS service account to carry out the rest of the test")
    sa = crud.service_account.create(db=session, obj_in=ServiceAccountCreateIn(**{
            "name": f"Integration Test Service Account - {test_school.id}",
            "type": "lms",
            "schools": [
                {
                    "country_code": "ATA",
                    "official_identifier": test_school.id,
                    "wriveted_identifier": test_school.wriveted_identifier
                }
            ],
            "info": {
                "msg": "Created for test purposes"
            }
        })
    )
    print(sa)

    yield sa

    crud.service_account.remove(db=session, id=sa.id)



@pytest.fixture()
def test_school_service_account_token(settings, service_account_for_test_school):
    access_token = create_access_token(
        subject=f"wriveted:service-account:{service_account_for_test_school.id}",
        expires_delta=timedelta(
            minutes=settings.SERVICE_ACCOUNT_ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )

    return access_token


@pytest.fixture()
def test_school_service_account_headers(test_school_service_account_token):
    return {
        "Authorization": f"bearer {test_school_service_account_token}"
    }
