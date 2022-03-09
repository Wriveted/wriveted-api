import collections
from importlib.util import LazyLoader
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Security
from sqlalchemy.orm import Session
from structlog import get_logger

from app import crud
from app.api.common.pagination import PaginatedQueryParams
from app.api.dependencies.security import get_current_active_superuser_or_backend_service_account, get_current_active_user_or_service_account
from app.db.session import get_session
from app.models import Edition
from app.schemas.edition import (
    EditionDetail,
    EditionBrief,
    EditionCreateIn,
    KnownAndTaggedEditionCounts,
)
from app.schemas.labelset import LabelSetPatch
from app.services.collections import create_missing_editions
from app.services.editions import compare_known_editions, get_definitive_isbn


logger = get_logger()

router = APIRouter(
    tags=["Labelsets"],
    dependencies=[Depends(get_current_active_superuser_or_backend_service_account)],
)

@router.patch("/labelsets", response_model=List[EditionBrief])
async def bulk_patch_labelsets(
    patches: list[LabelSetPatch],
    session: Session = Depends(get_session),
):
    for patch in patches:
        work = crud.work.find_by_isbn(session, patch.isbn)
        labelset = crud.labelset.get_or_create(session, work, False)
        labelset = crud.labelset.patch(session, labelset, patch.patch_data, False)

        # TODO: add to Huey's Picks booklist
        # if patch.huey_pick:
        #     work.booklists.append(crud.booklists.get_by_key("wriveted_hueypicks"))

        session.commit()