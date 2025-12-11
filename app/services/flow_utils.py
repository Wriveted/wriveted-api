from __future__ import annotations

from typing import Dict

from app.models.cms import ConnectionType

_TOKEN_TO_ENUM: Dict[str, ConnectionType] = {
    "DEFAULT": ConnectionType.DEFAULT,
    "SUCCESS": ConnectionType.SUCCESS,
    "FAILURE": ConnectionType.FAILURE,
    "$0": ConnectionType.OPTION_0,
    "$1": ConnectionType.OPTION_1,
}

_ENUM_TO_TOKEN: Dict[str, str] = {
    "DEFAULT": "DEFAULT",
    "SUCCESS": "SUCCESS",
    "FAILURE": "FAILURE",
    "OPTION_0": "$0",
    "OPTION_1": "$1",
}


def token_to_enum(token: str | None) -> ConnectionType:
    """Map a snapshot connection type token to ConnectionType enum.

    Unknown tokens (including 'CONDITIONAL') fall back to DEFAULT.
    """
    if not token:
        return ConnectionType.DEFAULT
    key = str(token).upper()
    return _TOKEN_TO_ENUM.get(key, ConnectionType.DEFAULT)


def enum_to_token(ct: ConnectionType) -> str:
    """Map a ConnectionType enum to a snapshot token string."""
    name = ct.name if hasattr(ct, "name") else str(ct)
    return _ENUM_TO_TOKEN.get(name, "DEFAULT")
