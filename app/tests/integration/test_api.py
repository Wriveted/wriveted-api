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
