from datetime import timedelta
from typing import List

from fastapi import Depends, APIRouter
from sqlalchemy.orm import Session
from structlog import get_logger

from app import crud
from app.api.common.pagination import PaginatedQueryParams
from app.api.dependencies.security import get_current_active_superuser
from app.config import get_settings
from app.db.session import get_session
from app.models import User, Event, ServiceAccount
from app.schemas.service_account import ServiceAccountCreateIn, ServiceAccountCreatedResponse, ServiceAccountBrief
from app.services.security import create_access_token

logger = get_logger()

router = APIRouter(
    tags=["Security"],
    dependencies=[
        Depends(get_current_active_superuser)
    ]
)


@router.get("/service-accounts", response_model=List[ServiceAccountBrief])
async def get_service_accounts(
        include_inactive: bool = False,
        current_user: User = Depends(get_current_active_superuser),
        pagination: PaginatedQueryParams = Depends(),
        session: Session = Depends(get_session)
):
    """
    List all service accounts.

    """
    logger.info("Listing service accounts", user=current_user)
    query = crud.service_account.get_all_query(db=session)
    if not include_inactive:
        query = query.where(ServiceAccount.is_active == True)

    query = crud.service_account.apply_pagination(query, skip=pagination.skip, limit=pagination.limit)

    return session.execute(query).scalars().all()


@router.post("/service-account", response_model=ServiceAccountCreatedResponse)
async def create_service_account(
        service_account_data: ServiceAccountCreateIn,
        current_user: User = Depends(get_current_active_superuser),
        session: Session = Depends(get_session)
):
    logger.info("Creating a new service account", user=current_user)

    new_service_account = crud.service_account.create(db=session, obj_in=service_account_data)

    session.add(Event(
        title="Service account created",
        description=f"Service account {new_service_account.name} created by {current_user}",
        user=current_user,
        service_account=new_service_account,
    ))
    session.commit()

    # Make a new access token for this service account
    settings = get_settings()
    access_token = create_access_token(
        subject=f"wriveted:service-account:{new_service_account.id}",
        expires_delta=timedelta(
            minutes=settings.SERVICE_ACCOUNT_ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )

    return {
        **ServiceAccountBrief.from_orm(new_service_account).dict(),
        "access_token": access_token
    }


@router.delete("/service-account/{service_account_id}", response_model=ServiceAccountBrief)
async def delete_service_account(
        service_account_id: str,
        current_user: User = Depends(get_current_active_superuser),
        session: Session = Depends(get_session)
):
    logger.info("Deleting a service account", user=current_user, service_account_id=service_account_id)

    service_account = crud.service_account.get_or_404(db=session, id=service_account_id)

    session.add(Event(
        title="Service account deleted",
        description=f"Service account {service_account.name} deleted by {current_user}",
        user=current_user,
        service_account=service_account,
    ))
    service_account.is_active = False
    session.commit()