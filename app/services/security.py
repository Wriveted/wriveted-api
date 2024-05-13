import datetime
from typing import Any, Optional, Union

from jose import jwt
from pydantic import BaseModel, field_validator

from app.config import get_settings

ALGORITHM = "HS256"


def get_raw_payload_from_access_token(token) -> dict[str, Any]:
    settings = get_settings()
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    return payload


class TokenPayload(BaseModel):
    sub: str
    iat: datetime
    exp: datetime

    @field_validator("sub")
    @classmethod
    def sub_must_start_with_wriveted(cls, v):
        if not v.startswith("wriveted") and ":" not in v:
            raise ValueError("Invalid JWT subject")
        return v.title()


def get_payload_from_access_token(token) -> TokenPayload:
    payload = get_raw_payload_from_access_token(token)
    return TokenPayload.model_validate(payload)


def create_access_token(
    subject: Union[str, Any],
    expires_delta: datetime.timedelta,
    extra_claims: Optional[dict[str, str]] = None,
) -> str:
    settings = get_settings()

    expire = datetime.datetime.now(datetime.UTC) + expires_delta

    to_encode = {
        "exp": expire,
        "iat": datetime.datetime.now(datetime.UTC),
        "sub": str(subject),
    }
    if extra_claims:
        to_encode.update(extra_claims)
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
