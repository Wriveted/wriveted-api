from uuid import UUID

from fastapi import Depends, HTTPException, Path
from fastapi_permissions import has_permission
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status

from app import crud
from app.api.dependencies.async_db_dep import DBSessionDep
from app.api.dependencies.collection import get_collection_from_id
from app.api.dependencies.security import get_active_principals
from app.db.session import get_session
from app.models.collection import Collection
from app.models.user import User


def get_user_from_id(
    user_id: UUID = Path(
        ..., description="UUID representing a unique user in the Wriveted database"
    ),
    session: Session = Depends(get_session),
):
    return crud.user.get_or_404(db=session, id=user_id)


class MaybeHasUserId(BaseModel):
    user_id: UUID | None = None


def get_optional_user_from_body(
    data: MaybeHasUserId,
    session: Session = Depends(get_session),
):
    return crud.user.get_or_404(db=session, id=data.user_id) if data.user_id else None


def get_and_validate_specified_user_from_body(
    user: User | None = Depends(get_optional_user_from_body),
    active_principals=Depends(get_active_principals),
) -> User | None:
    """
    Validate that the current user has permission to perform modifying operations [on/in lieu of] the specified user, returning the specified user if so.
    """
    if user is not None:
        if not has_permission(active_principals, "update", user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The current account is not allowed to perform an operation associated with that user",
            )
        return user


class HasReaderId(BaseModel):
    reader_id: UUID


def get_reader_from_body(
    data: HasReaderId,
    session: Session = Depends(get_session),
):
    return crud.user.get_or_404(db=session, id=data.reader_id)


class MaybeHasReaderId(BaseModel):
    reader_id: UUID | None = None


async def get_and_validate_collection_with_optional_reader(
    async_session: DBSessionDep,
    data: MaybeHasReaderId,
    collection: Collection = Depends(get_collection_from_id),
    active_principals=Depends(get_active_principals),
):
    reader = (
        (await crud.user.aget_or_404(db=async_session, id=data.reader_id))
        if data.reader_id
        else None
    )
    if reader is not None:
        if not has_permission(active_principals, "update", reader):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The current account is not allowed to perform an operation associated with that reader",
            )
        reader_principals = await get_active_principals(reader)
        if not has_permission(reader_principals, "read", collection):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The specified reader is not allowed to read that collection",
            )

    return collection
