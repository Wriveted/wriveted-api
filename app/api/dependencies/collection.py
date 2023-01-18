import uuid

from fastapi import Body, Depends, HTTPException, Path, Request
from fastapi_permissions import has_permission
from sqlalchemy.orm import Session

from app import crud
from app.api.dependencies.security import get_active_principals
from app.db.session import get_session


def get_collection_from_id(
    collection_id: uuid.UUID = Path(
        ..., description="UUID representing a unique collection of books"
    ),
    session: Session = Depends(get_session),
):
    return crud.collection.get_or_404(db=session, id=collection_id)


def get_collection_item_from_body(
    collection_item_id: int = Body("collection_item_id"),
    session: Session = Depends(get_session),
):
    return crud.collection.get_collection_item_or_404(
        db=session, collection_item_id=collection_item_id
    )


async def validate_collection_creation(
    request: Request,
    session: Session = Depends(get_session),
    principals: list = Depends(get_active_principals),
) -> any:
    body = await request.json()

    if school_id := body.get("school_id"):
        school = crud.school.get_by_wriveted_id_or_404(
            db=session, wriveted_id=school_id
        )
        if not has_permission(principals, "update", school):
            raise HTTPException(
                status_code=401, detail="Unauthorized to create collection for school"
            )
        if school.collection is not None:
            raise HTTPException(
                status_code=409,
                detail={
                    "msg": "School already has a collection. If intending to replace it, please use the PUT /collection/{collection_id} endpoint.",
                    "collection_id": school.collection.id,
                },
            )

    elif user_id := body.get("user_id"):
        user = crud.user.get_or_404(db=session, id=user_id)
        if not has_permission(principals, "update", user):
            raise HTTPException(
                status_code=401, detail="Unauthorized to create collection for user"
            )
        if user.collection is not None:
            raise HTTPException(
                status_code=409,
                detail={
                    "msg": "User already has a collection. If intending to replace it, please use the PUT /collection/{collection_id} endpoint.",
                    "collection_id": user.collection.id,
                },
            )
