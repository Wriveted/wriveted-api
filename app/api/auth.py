from datetime import datetime
from typing import Union
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi_cloudauth.firebase import FirebaseClaims, FirebaseCurrentUser
from pydantic import BaseModel
from sqlalchemy.orm import Session
from structlog import get_logger

from app import crud
from app.api.dependencies.security import (
    create_user_access_token,
    get_current_active_user_or_service_account,
    get_valid_token_data,
)
from app.config import get_settings
from app.db.session import get_session
from app.models import EventLevel, ServiceAccount, User
from app.models.user import UserAccountType
from app.schemas.auth import AccountType, AuthenticatedAccountBrief
from app.schemas.user import UserCreateIn, UserIdentity
from app.services.security import TokenPayload

logger = get_logger()
config = get_settings()

router = APIRouter(tags=["Security"])

get_current_firebase_user = FirebaseCurrentUser(project_id=config.FIREBASE_PROJECT_ID)

get_raw_info = get_current_firebase_user.claim(None)


class Token(BaseModel):
    access_token: str
    token_type: str


@router.get(
    "/auth/firebase",
    responses={
        401: {"description": "Unauthorized"},
        422: {"description": "Invalid data"},
    },
)
def secure_user_endpoint(
    firebase_user: FirebaseClaims = Depends(get_current_firebase_user),
    raw_data=Depends(get_raw_info),
    session: Session = Depends(get_session),
):
    """Login to Wriveted API by exchanging a valid Firebase token.

    This API is used to create access tokens for users that have logged into a Wriveted
    controlled Firebase application - usually with a federated Google account.

    The generated access token is a JSON Web Token (JWT) which contains a user specific unique
    identifier so Wriveted can recognize the user when that access token is provided as part of
    an API call.

    Note this API creates a new user if required, updates existing users with the latest SSO data
    (e.g. their profile picture).
    """

    # If we have gotten this far the user has a valid firebase token
    logger.debug("Auth with firebase endpoint called", firebase_user=firebase_user)
    logger.debug("Raw claim data", raw_firebase_claims=raw_data)
    assert raw_data["email_verified"], "Firebase hasn't checked the email address"
    assert (
        len(raw_data["name"]) > 0
    ), "Firebase credentials didn't include the users name"

    email = firebase_user.email
    picture = raw_data.get("picture")
    name = raw_data.get("name")

    user_data = UserCreateIn(
        name=name,
        email=email,
        info={
            "sign_in_provider": raw_data["firebase"].get("sign_in_provider"),
            "picture": picture,
        },
    )

    user, was_created = crud.user.get_or_create(session, user_data)
    if was_created:
        crud.event.create(
            session=session,
            title="User account created",
            description="",
            account=user,
            commit=False,
        )
    else:
        crud.event.create(
            session=session,
            title="User logged in",
            description="",
            account=user,
            level=EventLevel.DEBUG,
            commit=False,
        )
    logger.info("Request to login from user", user=user)

    if not user.is_active:
        raise HTTPException(status_code=401, detail="Inactive user")

    # Note this replaces the user's info with the SSO data including their name and info.
    # crud.user.update(db=session, db_obj=user, obj_in=user_data)
    # Instead we only update the fields we want
    if user.info is None:
        user.info = {}
    user.info["picture"] = picture
    user.info["sign_in_provider"] = raw_data["firebase"].get("sign_in_provider")

    user.last_login_at = datetime.utcnow()
    session.add(user)
    session.commit()

    wriveted_access_token = create_user_access_token(user)

    return {
        "access_token": wriveted_access_token,
        "token_type": "bearer",
    }


@router.post(
    "/auth/class-code",
    responses={
        401: {"description": "Unauthorized"},
        422: {"description": "Invalid data"},
    },
)
def student_user_auth(
    username: str,
    class_joining_code: str,
    session: Session = Depends(get_session),
):
    """Login to Wriveted API as a student by posting a valid username and class code.

    This API is used to create access tokens for existing student users.

    The generated access token is a JSON Web Token (JWT) which contains a user specific unique
    identifier so Wriveted can recognize the user when that access token is provided as part of
    an API call.

    Note this API doesn't create new users.
    """

    # Get the class by joining code or 401
    # Get the associated school
    # Get the user by username - if the school doesn't match -> 401


    # TODO check the school + user is active else 403 (difference being the server knows who you are)

    # If the user has been removed from the class we log them in anyway

    pass


@router.post(
    "/auth/register-student",
    response_model=UserIdentity
)
def create_student_user(
    first_name: str,
    last_initial: str,
    school_id: UUID,
    class_joining_code: str,
    session: Session = Depends(get_session),
):
    """Create a new student account associated with a school by posting a valid class code.

    The generated access token is a JSON Web Token (JWT) which contains a user specific unique
    identifier so Wriveted can recognize the user when that access token is provided as part of
    an API call.

    Note this API always creates a new user, to log in to an existing account see `/auth/class-code`
    """

    school = crud.school.get_by_wriveted_id_or_404(
        db=session, wriveted_id=school_id
    )

    # TODO check the class joining code belongs to this school

    # TODO generate a valid username based on the name
    name = f'{first_name} {last_initial}'
    username = ...

    new_user = User(
        type=UserAccountType.STUDENT,
        name=name,
        email=None,
        username=username,
        info={
            "sign_in_provider": "class-code"
        },
    )

    crud.event.create(
        session=session,
        title="Student account created",
        description=f"",
        account=new_user,
        school=school,
        commit=False,
    )
    session.commit()
    session.refresh(new_user)

    return new_user


@router.get("/auth/me", response_model=AuthenticatedAccountBrief)
async def get_current_user(
    token_data: TokenPayload = Depends(get_valid_token_data),
    current_user_or_service_account: Union[User, ServiceAccount] = Depends(
        get_current_active_user_or_service_account
    ),
):
    """
    Test that the presented credentials are valid, returning details on the logged in user or service account.
    """
    logger.debug("Testing user token", account=current_user_or_service_account)
    if isinstance(current_user_or_service_account, User):
        return AuthenticatedAccountBrief(
            account_type=AccountType.user,
            user=current_user_or_service_account,
            token_expiry=token_data.exp,
        )
    elif isinstance(current_user_or_service_account, ServiceAccount):
        return AuthenticatedAccountBrief(
            account_type=AccountType.service_account,
            service_account=current_user_or_service_account,
            token_expiry=token_data.exp,
        )
    else:
        raise NotImplemented("Hmm")
