from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from structlog import get_logger
from app import crud
from app.api.dependencies.security import get_current_active_superuser_or_backend_service_account, get_current_active_user_or_service_account
from app.db.session import get_session
from app.schemas.edition import EditionBrief
from app.schemas.labelset import LabelSetPatch

logger = get_logger()

router = APIRouter(
    tags=["Labelsets"],
    dependencies=[Depends(get_current_active_superuser_or_backend_service_account)],
)

@router.patch("/labelsets")
async def bulk_patch_labelsets(
    patches: list[LabelSetPatch],
    session: Session = Depends(get_session),
):
    patched = 0
    unknown = 0
    errors = 0

    for patch in patches:
        work = crud.work.find_by_isbn(session, patch.isbn)
        if not work:
            unknown += 1
            continue

        try:
            labelset = crud.labelset.get_or_create(session, work, False)
            labelset = crud.labelset.patch(session, labelset, patch.patch_data, False)

            # TODO: add to Huey's Picks booklist
            # if patch.huey_pick:
            #     work.booklists.append(crud.booklists.get_by_key("wriveted_hueypicks"))

            session.commit()
            patched += 1
        except Exception as ex:
            print(ex)
            errors += 1