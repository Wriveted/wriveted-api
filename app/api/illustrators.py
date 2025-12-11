from typing import List

from fastapi import APIRouter, Depends, Security
from sqlalchemy.orm import Session

from app.api.common.pagination import PaginatedQueryParams
from app.api.dependencies.security import get_current_active_user_or_service_account
from app.db.session import get_session
from app.repositories.illustrator_repository import illustrator_repository
from app.schemas.illustrator import IllustratorBrief

router = APIRouter(
    tags=["Authors"],
    dependencies=[Security(get_current_active_user_or_service_account)],
)


@router.get("/illustrators", response_model=List[IllustratorBrief])
async def get_illustrators(
    pagination: PaginatedQueryParams = Depends(),
    session: Session = Depends(get_session),
):
    return illustrator_repository.get_all(
        session, skip=pagination.skip, limit=pagination.limit
    )


@router.get("/illustrators/{illustrator_id}", response_model=IllustratorBrief)
async def get_illustrator_by_id(
    illustrator_id: str, session: Session = Depends(get_session)
):
    return illustrator_repository.get_or_404(db=session, id=int(illustrator_id))
