import base64
import hashlib
import hmac
import secrets
from datetime import timedelta
from typing import Optional, Union

from fastapi import Depends, Header, HTTPException, Request
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
    OAuth2PasswordBearer,
)
from fastapi_permissions import Authenticated, Everyone
from jose import jwt
from pydantic import ValidationError
from sqlalchemy.orm import Session
from starlette import status
from structlog import get_logger

from app import crud
from app.config import get_settings
from app.db.session import get_session
from app.models import ServiceAccount, ServiceAccountType, User
from app.models.user import UserAccountType
from app.services.security import (
    TokenPayload,
    create_access_token,
    get_payload_from_access_token,
)

settings = get_settings()
logger = get_logger()

auth_scheme = OAuth2PasswordBearer(tokenUrl="/auth/access-token")

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_auth_header_data(
    http_auth: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
) -> str:

    if http_auth is None:
        raise credentials_exception

    token = http_auth.credentials

    if not token:
        raise credentials_exception

    return token


def get_valid_token_data(token: str = Depends(get_auth_header_data)) -> TokenPayload:
    # logger.debug("Headers contain an Authorization component")
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
        with db as session:
            user = crud.user.get(session, id=identifier)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        return user


def get_optional_service_account(
    db: Session = Depends(get_session),
    token_data: TokenPayload = Depends(get_valid_token_data),
) -> Optional[ServiceAccount]:
    # The subject of the JWT is either a user identifier or service account identifier
    # "wriveted:service-account:XXX" or "wriveted:user-account:XXX"
    aud, access_token_type, identifier = token_data.sub.lower().split(":")

    if access_token_type == "service-account":
        with db as session:
            return crud.service_account.get_or_404(session, id=identifier)


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
    maybe_service_account: Optional[ServiceAccount] = Depends(
        get_optional_service_account
    ),
) -> Union[User, ServiceAccount]:
    # We need either a valid user or service account given the auth token
    if maybe_user is not None and maybe_user.is_active:
        return maybe_user
    elif maybe_service_account is not None and maybe_service_account.is_active:
        return maybe_service_account
    else:
        raise HTTPException(status_code=400, detail="Inactive account")


def get_current_active_superuser_or_backend_service_account(
    user_or_service_account: Union[User, ServiceAccount] = Depends(
        get_current_active_user_or_service_account
    ),
) -> Union[User, ServiceAccount]:
    if isinstance(user_or_service_account, User):
        if not user_or_service_account.type == UserAccountType.WRIVETED:
            raise HTTPException(status_code=403, detail="Insufficient privileges")
    elif isinstance(user_or_service_account, ServiceAccount):
        if not user_or_service_account.type == ServiceAccountType.BACKEND:
            raise HTTPException(status_code=403, detail="Insufficient privileges")
    return user_or_service_account


def get_current_active_superuser(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Require administrator access
    """
    if not current_user.type == UserAccountType.WRIVETED:
        raise HTTPException(status_code=403, detail="Insufficient privileges")
    return current_user


def get_active_principals(
    maybe_user: Optional[User] = Depends(get_optional_user),
    maybe_service_account: Optional[ServiceAccount] = Depends(
        get_optional_service_account
    ),
):
    """
    RBAC Access Control using https://github.com/holgi/fastapi-permissions

    Principals:
    - role:admin
    - role:educator
    - role:school
    - role:student
    - role:kiosk
    - role:reader
    - role:parent

    - user:{id}
    - school:{id}  (this just means associated with this school)
    - student:{school-id}
    - educator:{school-id}
    - schooladmin:{school-id}
    - parent:{child-id}
    - child:{parent-id}

    - Authenticated
    - Everyone

    Future Principals:
    - member:{group-id}

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

            case UserAccountType.EDUCATOR:
                principals.append("role:educator")
                principals.append("role:school")
                principals.append(f"school:{user.school_id}")
                principals.append(f"educator:{user.school_id}")

            case UserAccountType.SCHOOL_ADMIN:
                principals.append("role:educator")
                principals.append("role:school")
                principals.append(f"school:{user.school_id}")
                principals.append(f"educator:{user.school_id}")
                principals.append(f"schooladmin:{user.school_id}")

            case UserAccountType.STUDENT:
                principals.append("role:reader")
                principals.append("role:student")
                principals.append("role:school")
                principals.append(f"school:{user.school_id}")
                principals.append(f"student:{user.school_id}")
                if user.parent:
                    principals.append(f"child:{user.parent_id}")

            case UserAccountType.PUBLIC:
                principals.append("role:reader")
                if user.parent:
                    principals.append(f"child:{user.parent_id}")

            case UserAccountType.PARENT:
                principals.append("role:parent")
                for child in user.children:
                    principals.append(f"parent:{child.id}")

        # All users have a user specific role:
        principals.append(f"user:{user.id}")

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


def create_user_access_token(user, expires_delta=None):
    if expires_delta is None:
        delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    else:
        delta = expires_delta
    wriveted_access_token = create_access_token(
        subject=f"Wriveted:User-Account:{user.id}",
        # extra_claims={},
        expires_delta=delta,
    )
    logger.debug("Access token generated for user", user=user)
    return wriveted_access_token


async def verify_shopify_hmac(
    request: Request, x_shopify_hmac_sha256: str | None = Header(default=None)
):
    body = await request.body()
    digest = hmac.new(
        settings.SHOPIFY_HMAC_SECRET.encode("utf-8"),
        body,
        hashlib.sha256,
    ).digest()
    computed_hmac = base64.b64encode(digest)
    valid = secrets.compare_digest(computed_hmac, x_shopify_hmac_sha256.encode("utf-8"))
    if not valid:
        raise HTTPException(status_code=403, detail="Invalid SHA-256 HMAC")
