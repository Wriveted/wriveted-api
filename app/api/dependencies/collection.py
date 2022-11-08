import uuid

from fastapi import Body, Depends, HTTPException, Path, Request
from fastapi_permissions import has_permission, Allow, All, Everyone, Authenticated
from sqlalchemy.orm import Session

from app import crud
from app.api.dependencies.security import get_active_principals
from app.db.session import get_session
from app.models.school import School
from app.models.user import User
from app.permissions import Permission
from app.schemas.collection import CollectionCreateIn


def get_collection_from_id(
    collection_id: uuid.UUID = Path(
        ..., description="UUID representing a unique collection of books"
    ),
    session: Session = Depends(get_session),
):
    return crud.collection.get_or_404(db=session, id=collection_id)


async def validate_collection_creation(
    request: Request,
    session: Session = Depends(get_session),
    principals: list = Depends(get_active_principals),
) -> any:
    body = await request.json()

    if school_id := body.get("school_id"):
        if not has_permission(
            principals,
            "update",
            crud.school.get_or_404(db=session, id=school_id),
        ):
            raise HTTPException(
                status_code=401, detail="Unauthorized to create collection for school"
            )

    elif user_id := body.get("user_id"):
        if not has_permission(
            principals,
            "update",
            crud.user.get_or_404(db=session, id=user_id),
        ):
            raise HTTPException(
                status_code=401, detail="Unauthorized to create collection for user"
            )
