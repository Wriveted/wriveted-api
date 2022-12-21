from datetime import datetime, timedelta
from typing import Any, Optional, Union

from jose import jwt
from pydantic import BaseModel, validator

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

    @validator("sub")
    def sub_must_start_with_wriveted(cls, v):
        if not v.startswith("wriveted") and ":" not in v:
            raise ValueError("Invalid JWT subject")
        return v.title()


def get_payload_from_access_token(token) -> TokenPayload:
    payload = get_raw_payload_from_access_token(token)
    return TokenPayload.parse_obj(payload)


def create_access_token(
    subject: Union[str, Any],
    expires_delta: timedelta,
    extra_claims: Optional[dict[str, str]] = None,
) -> str:
    settings = get_settings()

    expire = datetime.utcnow() + expires_delta

    to_encode = {"exp": expire, "iat": datetime.utcnow(), "sub": str(subject)}
    if extra_claims:
        to_encode.update(extra_claims)
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
