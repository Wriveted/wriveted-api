import base64
import json
import os
import pathlib

import httpx
import pydantic
import pytest
import time

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from starlette import status


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


def test_school_exists(client, backend_service_account_headers):
    response = client.get(
        "v1/school/not-a-uuid/exists", headers=backend_service_account_headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


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
    settings,
    test_school,
    service_account_for_test_school,
    test_school_service_account_headers,
):
    school_id = test_school.wriveted_identifier
    get_initial_school_details_response = client.get(
        f"/v1/school/{school_id}",
        headers=test_school_service_account_headers,
    )
    get_initial_school_details_response.raise_for_status()
    initial_details = get_initial_school_details_response.json()
    assert initial_details["name"] == test_school.name

    update_response = client.put(
        f"/v1/school/{school_id}",
        headers=test_school_service_account_headers,
        json={"name": "cool school"},
    )
    update_response.raise_for_status()
    assert update_response.json()["name"] == "cool school"

    get_school_details_response = client.get(
        f"/v1/school/{school_id}",
        headers=test_school_service_account_headers,
    )
    get_school_details_response.raise_for_status()
    assert get_school_details_response.json()["name"] == "cool school"


def test_disallowed_update_to_school(
    client,
    settings,
    test_school,
    service_account_for_test_school,
    test_school_service_account_headers,
):

    school_id = test_school.wriveted_identifier
    get_initial_school_details_response = client.get(
        f"/v1/school/{school_id}",
        headers=test_school_service_account_headers,
    )
    get_initial_school_details_response.raise_for_status()
    initial_details = get_initial_school_details_response.json()
    assert initial_details["name"] == test_school.name

    update_response = client.put(
        f"/v1/school/{school_id}",
        headers=test_school_service_account_headers,
        json={"country_code": "NZL"},
    )
    update_response.raise_for_status()
    assert update_response.json()["country_code"] == test_school.country_code
