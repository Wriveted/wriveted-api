import enum
from typing import Optional, Union, List

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, HTTPAuthorizationCredentials, HTTPBearer
from fastapi_permissions import Everyone, Authenticated

from jose import jwt
from pydantic import ValidationError
from sqlalchemy.orm import Session
from starlette import status
from structlog import get_logger

from app import crud
from app.api.dependencies.school import get_school_from_path
from app.db.session import get_session
from app.models import User, ServiceAccount, ServiceAccountType, School
from app.models.user import UserAccountType
from app.services.security import create_access_token, get_payload_from_access_token, TokenPayload

logger = get_logger()

auth_scheme = OAuth2PasswordBearer(tokenUrl="/auth/access-token")

credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_auth_header_data(
        http_auth: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))
) -> str:

    if http_auth is None:
        raise credentials_exception

    token = http_auth.credentials

    if not token:
        raise credentials_exception

    return token


def get_valid_token_data(token: str = Depends(get_auth_header_data)) -> TokenPayload:
    #logger.debug("Headers contain an Authorization component")
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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found")
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


def get_current_user(current_user: Optional[User] = Depends(get_optional_user)) -> User:
    if current_user is None:
        raise HTTPException(status_code=403, detail="API requires a user")
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
        if not user_or_service_account.type == UserAccountType.WRIVETED:
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
    if not current_user.type == UserAccountType.WRIVETED:
        raise HTTPException(
            status_code=403, detail="Insufficient privileges"
        )
    return current_user



def get_active_principals(
    maybe_user: Optional[User] = Depends(get_optional_user),
    maybe_service_account: Optional[ServiceAccount] = Depends(get_optional_service_account),
):
    """
    RBAC Access Control using https://github.com/holgi/fastapi-permissions

    Principals:
    - role:admin
    - role:lms
    - role:library
    - role:school
    - role:kiosk
    - user:{id}
    - school:{id}
    - Authenticated
    - Everyone

    Future Principals:
    - role:student
    - role:child
    - role:parent
    - role:teacher

    Permissions:
    - CRUD (create, read, update, delete)

    Future permissions?
    - batch
    - share
    """

    principals = [Everyone]

    if maybe_user is not None and maybe_user.is_active:
        user = maybe_user
        principals.append(Authenticated)
        match user.type:
            case UserAccountType.WRIVETED:
                principals.append("role:admin")
            case UserAccountType.LMS:
                principals.append("role:lms")
            case UserAccountType.LIBRARY:
                principals.append("role:library")
            case UserAccountType.PUBLIC:
                # No special roles given to the default public
                # user type
                pass

        # All users have a user specific role:
        principals.append(f'user:{user.id}')

        # Users can optionally be associated with a school:
        if user.school_id_as_admin is not None:
            principals.append(f'school:{user.school_id_as_admin}')

    elif maybe_service_account is not None and maybe_service_account.is_active:
        service_account = maybe_service_account
        principals.append(Authenticated)

        match service_account.type:
            case ServiceAccountType.BACKEND:
                principals.append("role:admin")
            case ServiceAccountType.LMS:
                principals.append("role:lms")
            case ServiceAccountType.SCHOOL:
                principals.append("role:school")
                principals.append("role:library")
            case ServiceAccountType.KIOSK:
                principals.append("role:kiosk")

        # Service accounts can optionally be associated with multiple schools:
        for school in service_account.schools:
            principals.append(f"school:{school.id}")

    return principals


def create_user_access_token(user):
    wriveted_access_token = create_access_token(
        subject=f"Wriveted:User-Account:{user.id}",
        # extra_claims={}
    )
    logger.debug("Access token generated for user", user=user)
    return wriveted_access_token
