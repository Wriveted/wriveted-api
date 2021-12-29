from typing import Union

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from fastapi_cloudauth.firebase import FirebaseCurrentUser, FirebaseClaims
from structlog import get_logger

from app import crud
from app.api.dependencies.security import get_current_active_user, get_current_active_user_or_service_account
from app.config import get_settings
from app.db.session import get_session
from app.models import User, ServiceAccount
from app.schemas.service_account import ServiceAccountBrief
from app.schemas.user import UserBrief, UserCreateIn, UserDetail
from app.services.security import create_access_token

logger = get_logger()
config = get_settings()

router = APIRouter(
    tags=["Security"]
)

get_current_firebase_user = FirebaseCurrentUser(
    project_id=config.FIREBASE_PROJECT_ID
)

get_raw_info = get_current_firebase_user.claim(None)


class Token(BaseModel):
    access_token: str
    token_type: str


@router.get(
    "/auth/firebase",
    responses={
        401: {"description": "Unauthorized"},
        422: {"description": "Invalid data"}
    }
)
def secure_user_endpoint(
        firebase_user: FirebaseClaims = Depends(get_current_firebase_user),
        raw_data = Depends(get_raw_info),
        session: Session = Depends(get_session),
):
    """Login to Wriveted API by exchanging a firebase token.

    Creates a new user if required.
    """

    # If we have gotten this far the user has a valid firebase token
    logger.debug("Auth with firebase endpoint called", firebase_user=firebase_user)
    logger.debug("Raw claim data", raw_firebase_claims=raw_data)
    assert raw_data['email_verified'], "Firebase hasn't checked the email address"
    assert len(raw_data['name']) > 0, "Firebase credentials didn't include the users name"

    email = firebase_user.email
    picture = raw_data.get('picture')
    name = raw_data.get('name')

    user_data = UserCreateIn(
        name=name,
        email=email,
        info={
            "sign_in_provider": raw_data['firebase'].get("sign_in_provider"),
            "picture": picture
        }
    )

    user = crud.user.get_or_create(session, user_data)
    logger.info("Request to login from user", user=user)

    if not user.is_active:
        raise HTTPException(status_code=401, detail="Inactive user")

    wriveted_access_token = create_access_token(
        subject=f"wriveted:user-account:{user.id}",
        #extra_claims={}
    )
    logger.info("Access token generated for user", token=wriveted_access_token)

    return {
        "access_token": wriveted_access_token,
        "token_type": "bearer",
    }


@router.get("/auth/me", response_model=Union[UserDetail, ServiceAccountBrief])
async def get_current_user(
        current_user_or_service_account: Union[User, ServiceAccount] = Depends(get_current_active_user_or_service_account)
):
    """
    Test that the presented credentials are valid, returning details on the logged in user or service account.
    """
    logger.info("Testing user token", account=current_user_or_service_account)
    return current_user_or_service_account

