import uuid

from starlette import status


def test_read_openapi_spec(client):
    response = client.get("openapi.json")
    assert response.status_code == status.HTTP_200_OK


def test_read_version(client):
    response = client.get("v1/version")
    assert "database" in response.text
    assert response.status_code == status.HTTP_200_OK


def test_auth_me_api_requires_auth(client):
    response = client.get("v1/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_auth_me_api_with_auth(client, backend_service_account_headers):
    response = client.get("v1/auth/me", headers=backend_service_account_headers)
    assert response.status_code == status.HTTP_200_OK


def test_list_service_accounts(client, backend_service_account_headers):
    response = client.get(
        "v1/service-accounts", headers=backend_service_account_headers
    )
    assert response.status_code == status.HTTP_200_OK


def test_list_schools(client, backend_service_account_headers, test_school):
    response = client.get("v1/schools", headers=backend_service_account_headers)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) >= 1


def test_list_schools_filter_by_collection(
    client, backend_service_account_headers, test_school_with_collection
):
    response = client.get(
        "v1/schools",
        params={
            "connected_collection": True,
            "official_identifier": test_school_with_collection.official_identifier,
        },
        headers=backend_service_account_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) >= 1
    assert data[0]["wriveted_identifier"] == str(
        test_school_with_collection.wriveted_identifier
    )
    assert data[0]["collection_count"] > 0


def test_school_exists_bad_uuid(client, backend_service_account_headers):
    response = client.get(
        "v1/school/not-a-uuid/exists", headers=backend_service_account_headers
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_school_exists_missing_uuid(client, backend_service_account_headers):
    valid_uuid = uuid.uuid4()
    response = client.get(
        f"v1/school/{valid_uuid}/exists", headers=backend_service_account_headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_school_exists(client, backend_service_account_headers, test_school):
    valid_uuid = test_school.wriveted_identifier
    response = client.get(
        f"v1/school/{valid_uuid}/exists", headers=backend_service_account_headers
    )
    assert response.status_code == status.HTTP_200_OK


def test_get_own_service_account_detail(
    client, backend_service_account, backend_service_account_headers
):
    response = client.get(
        f"v1/service-account/{backend_service_account.id}",
        headers=backend_service_account_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert all(
        expected_key in data.keys()
        for expected_key in {
            "created_at",
            "events",
            "id",
            "info",
            "name",
            "is_active",
            "type",
        }
    )
    assert data["type"] == "backend"


def test_update_school_name(
    client,
    test_school,
    lms_service_account_headers_for_school,
):
    school_id = test_school.wriveted_identifier
    get_initial_school_details_response = client.get(
        f"/v1/school/{school_id}",
        headers=lms_service_account_headers_for_school,
    )
    get_initial_school_details_response.raise_for_status()
    initial_details = get_initial_school_details_response.json()
    assert initial_details["name"] == test_school.name

    update_response = client.patch(
        f"/v1/school/{school_id}",
        headers=lms_service_account_headers_for_school,
        json={"name": "cool school"},
    )
    update_response.raise_for_status()
    assert update_response.json()["name"] == "cool school"

    get_school_details_response = client.get(
        f"/v1/school/{school_id}",
        headers=lms_service_account_headers_for_school,
    )
    get_school_details_response.raise_for_status()
    assert get_school_details_response.json()["name"] == "cool school"


def test_update_school_state(
    client,
    test_school,
    admin_of_test_school_headers,
):
    school_id = test_school.wriveted_identifier
    get_initial_school_details_response = client.get(
        f"/v1/school/{school_id}",
        headers=admin_of_test_school_headers,
    )
    get_initial_school_details_response.raise_for_status()
    initial_details = get_initial_school_details_response.json()
    assert "state" in initial_details

    update_response = client.patch(
        f"/v1/school/{school_id}",
        headers=admin_of_test_school_headers,
        json={"status": "pending"},
    )
    update_response.raise_for_status()
    assert update_response.json()["state"] == "pending"
    client.patch(
        f"/v1/school/{school_id}",
        headers=admin_of_test_school_headers,
        json={"status": "active"},
    )
    get_school_details_response = client.get(
        f"/v1/school/{school_id}",
        headers=admin_of_test_school_headers,
    )
    get_school_details_response.raise_for_status()
    assert get_school_details_response.json()["state"] == "active"


def test_allowed_update_to_school(
    client,
    test_school,
    lms_service_account_headers_for_school,
):

    school_id = test_school.wriveted_identifier
    get_initial_school_details_response = client.get(
        f"/v1/school/{school_id}",
        headers=lms_service_account_headers_for_school,
    )
    get_initial_school_details_response.raise_for_status()
    initial_details = get_initial_school_details_response.json()
    assert initial_details["name"] == test_school.name

    update_response = client.patch(
        f"/v1/school/{school_id}",
        headers=lms_service_account_headers_for_school,
        json={"country_code": "NZL"},
    )
    update_response.raise_for_status()
    assert update_response.json()["country_code"] == test_school.country_code


def test_get_school_experiments(
    client,
    test_school,
    lms_service_account_headers_for_school,
):

    school_id = test_school.wriveted_identifier
    get_school_details_response = client.get(
        f"/v1/school/{school_id}",
        headers=lms_service_account_headers_for_school,
    )
    get_school_details_response.raise_for_status()
    details = get_school_details_response.json()
    assert "experiments" in details["info"]
    assert "no-jokes" in details["info"]["experiments"]
