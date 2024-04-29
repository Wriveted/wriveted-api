from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_session

DBSessionDep = Annotated[AsyncSession, Depends(get_async_session)]
