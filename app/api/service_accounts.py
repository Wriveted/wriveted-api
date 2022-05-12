from datetime import timedelta
from typing import List, Union

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from structlog import get_logger

from app import crud
from app.api.common.pagination import PaginatedQueryParams
from app.api.dependencies.security import (
    get_current_active_superuser,
    get_current_active_superuser_or_backend_service_account,
    get_current_active_user_or_service_account,
)
from app.config import get_settings
from app.db.session import get_session
from app.models import Event, ServiceAccount, User
from app.schemas.service_account import (
    ServiceAccountBrief,
    ServiceAccountCreatedResponse,
    ServiceAccountCreateIn,
    ServiceAccountDetail,
    ServiceAccountUpdateIn,
)
from app.services.security import create_access_token

logger = get_logger()

router = APIRouter(
    tags=["Security"],
    dependencies=[Depends(get_current_active_superuser_or_backend_service_account)],
)


@router.get("/service-accounts", response_model=List[ServiceAccountBrief])
async def get_service_accounts(
    include_inactive: bool = False,
    current_account: Union[User, ServiceAccount] = Depends(
        get_current_active_user_or_service_account
    ),
    pagination: PaginatedQueryParams = Depends(),
    session: Session = Depends(get_session),
):
    """
    List all service accounts.

    """
    logger.info("Listing service accounts", requester=current_account)
    query = crud.service_account.get_all_query(db=session)
    if not include_inactive:
        query = query.where(ServiceAccount.is_active == True)

    query = crud.service_account.apply_pagination(
        query, skip=pagination.skip, limit=pagination.limit
    )

    return session.execute(query).scalars().all()


@router.post("/service-account", response_model=ServiceAccountCreatedResponse)
async def create_service_account(
    service_account_data: ServiceAccountCreateIn,
    current_account: Union[User, ServiceAccount] = Depends(
        get_current_active_user_or_service_account
    ),
    session: Session = Depends(get_session),
):
    logger.info("Creating a new service account", requester=current_account)

    new_service_account = crud.service_account.create(
        db=session, obj_in=service_account_data
    )

    crud.event.create(
        session=session,
        title="{new_service_account.name} service account created",
        description=f"Service account '{new_service_account.name}' created by '{current_account.name}'",
        account=current_account,
    )

    # Make a new access token for this service account
    settings = get_settings()
    access_token = create_access_token(
        subject=f"wriveted:service-account:{new_service_account.id}",
        expires_delta=timedelta(
            minutes=settings.SERVICE_ACCOUNT_ACCESS_TOKEN_EXPIRE_MINUTES
        ),
    )

    return {
        **ServiceAccountBrief.from_orm(new_service_account).dict(),
        "access_token": access_token,
    }


@router.get(
    "/service-account/{service_account_id}", response_model=ServiceAccountDetail
)
async def get_service_account_detail(
    service_account_id: str, session: Session = Depends(get_session)
):
    return crud.service_account.get_or_404(db=session, id=service_account_id)


@router.put(
    "/service-account/{service_account_id}", response_model=ServiceAccountDetail
)
async def update_service_account(
    service_account_id: str,
    service_account_data: ServiceAccountUpdateIn,
    session: Session = Depends(get_session),
):
    service_account = crud.service_account.get_or_404(db=session, id=service_account_id)
    return crud.service_account.update(
        db=session, db_obj=service_account, obj_in=service_account_data
    )


@router.delete(
    "/service-account/{service_account_id}", response_model=ServiceAccountBrief
)
async def delete_service_account(
    service_account_id: str,
    current_user: User = Depends(get_current_active_superuser),
    session: Session = Depends(get_session),
):
    logger.info(
        "Deleting a service account",
        user=current_user,
        service_account_id=service_account_id,
    )

    service_account = crud.service_account.get_or_404(db=session, id=service_account_id)

    session.add(
        Event(
            title="Service account deleted",
            info={
                "description": f"Service account {service_account.name} deleted by {current_user}"
            },
            user=current_user,
            service_account=service_account,
        )
    )
    service_account.is_active = False
    session.commit()
