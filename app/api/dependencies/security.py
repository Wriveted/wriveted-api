from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, HTTPAuthorizationCredentials, HTTPBearer

from jose import jwt
from pydantic import ValidationError
from sqlalchemy.orm import Session
from starlette import status
from structlog import get_logger

from app import crud
from app.db.session import get_session
from app.models import User
from app.services.security import get_payload_from_access_token, TokenPayload


logger = get_logger()

auth_scheme = OAuth2PasswordBearer(tokenUrl="/auth/access-token")


def get_auth_header_data(
    http_auth: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))
) -> str:
    token = http_auth.credentials

    logger.info("Header", authorization=token)

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception

    return token


def get_valid_token_data(token: str = Depends(get_auth_header_data)) -> TokenPayload:
    logger.debug("Have an auth token", token=token)
    try:
        return get_payload_from_access_token(token)
    except (jwt.JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )


def get_current_user(
    db: Session = Depends(get_session),
    token_data: TokenPayload = Depends(get_valid_token_data),
) -> User:
    # The subject of the JWT is our user identifier
    user = crud.user.get(db, id=token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def get_current_active_superuser(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="Insufficient privileges"
        )
    return current_user

