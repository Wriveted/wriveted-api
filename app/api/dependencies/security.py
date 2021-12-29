from typing import Optional, Union

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, HTTPAuthorizationCredentials, HTTPBearer

from jose import jwt
from pydantic import ValidationError
from sqlalchemy.orm import Session
from starlette import status
from structlog import get_logger

from app import crud
from app.api.dependencies.school import get_school_from_path
from app.db.session import get_session
from app.models import User, ServiceAccount, ServiceAccountType, School
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


def get_optional_user(
    db: Session = Depends(get_session),
    token_data: TokenPayload = Depends(get_valid_token_data),
) -> Optional[User]:
    # The subject of the JWT is either a user identifier or service account identifier
    # "wriveted:service-account:XXX" or "wriveted:user-account:XXX"
    aud, access_token_type, identifier = token_data.sub.lower().split(":")

    if access_token_type == "user-account":
        user = crud.user.get(db, id=identifier)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user


def get_optional_service_account(
    db: Session = Depends(get_session),
    token_data: TokenPayload = Depends(get_valid_token_data),
) -> Optional[ServiceAccount]:
    # The subject of the JWT is either a user identifier or service account identifier
    # "wriveted:service-account:XXX" or "wriveted:user-account:XXX"
    aud, access_token_type, identifier = token_data.sub.lower().split(":")

    if access_token_type == "service-account":
        return crud.service_account.get_or_404(db, id=identifier)


def get_current_user(
    db: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_optional_user),
) -> User:
    assert current_user is not None
    return current_user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def get_current_active_user_or_service_account(
    maybe_user: Optional[User] = Depends(get_optional_user),
    maybe_service_account: Optional[ServiceAccount] = Depends(get_optional_service_account),
) -> Union[User, ServiceAccount]:

    # We need either a valid user or service account given the auth token
    if maybe_user is not None and maybe_user.is_active:
        return maybe_user
    elif maybe_service_account is not None and maybe_service_account.is_active:
        return maybe_service_account
    else:
        raise HTTPException(status_code=400, detail="Inactive account")


def get_current_active_superuser_or_backend_service_account(
    user_or_service_account: Union[User, ServiceAccount] = Depends(get_current_active_user_or_service_account),
) -> Union[User, ServiceAccount]:
    if isinstance(user_or_service_account, User):
        if not user_or_service_account.is_superuser:
            raise HTTPException(
                status_code=403, detail="Insufficient privileges"
            )
    elif isinstance(user_or_service_account, ServiceAccount):
        if not user_or_service_account.type == ServiceAccountType.BACKEND:
            raise HTTPException(
                status_code=403, detail="Insufficient privileges"
            )
    return user_or_service_account


def get_current_active_superuser(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Require administrator access
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="Insufficient privileges"
        )
    return current_user


def get_account_allowed_to_update_school(
        account = Depends(get_current_active_user_or_service_account),
        school: School = Depends(get_school_from_path)
):
    permission_exception = HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permission"
    )
    if isinstance(account, User):
        if not account.is_superuser and account.school_id != school.id:
            raise permission_exception
    elif isinstance(account, ServiceAccount):
        if account.type not in {ServiceAccountType.BACKEND, ServiceAccountType.LMS, ServiceAccountType.SCHOOL}:
            raise permission_exception
    return account