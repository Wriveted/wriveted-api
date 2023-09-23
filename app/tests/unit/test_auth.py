import datetime
import time

import pytest
from jose import ExpiredSignatureError
from pydantic import ValidationError
from pytest import approx

from app.api.dependencies.security import create_user_access_token
from app.config import get_settings
from app.models import User
from app.services.security import (
    create_access_token,
    get_payload_from_access_token,
    get_raw_payload_from_access_token,
)


def test_create_token():
    test_user = User(id=0)
    token = create_user_access_token(test_user)
    payload = get_payload_from_access_token(token)
    assert payload.sub == "Wriveted:User-Account:0"
    assert isinstance(payload.exp, datetime.datetime)
    assert isinstance(payload.iat, datetime.datetime)
    assert payload.iat < payload.exp

    valid_for = payload.exp - payload.iat
    assert valid_for.total_seconds() / 60 == approx(
        float(get_settings().ACCESS_TOKEN_EXPIRE_MINUTES)
    )


def test_extra_claims_propogated():
    token = create_access_token(
        subject="Wriveted:User-Account:0",
        extra_claims={"test-claim": "secret"},
        expires_delta=datetime.timedelta(minutes=1),
    )

    raw_payload = get_raw_payload_from_access_token(token)

    assert raw_payload["sub"] == "Wriveted:User-Account:0"
    assert "test-claim" in raw_payload
    assert raw_payload["test-claim"] == "secret"


def test_token_with_invalid_subject_rejected():
    token = create_access_token(
        subject="test-subject", expires_delta=datetime.timedelta(seconds=60)
    )
    with pytest.raises(ValidationError):
        get_payload_from_access_token(token)


def test_expired_token_rejected():
    token = create_access_token(
        subject="Wriveted:user-account:1", expires_delta=datetime.timedelta(seconds=1)
    )
    get_payload_from_access_token(token)
    time.sleep(2)

    with pytest.raises(ExpiredSignatureError):
        get_payload_from_access_token(token)
