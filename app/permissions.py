from fastapi import HTTPException
from fastapi_permissions import configure_permissions
from starlette import status

from app.api.dependencies.security import get_active_principals


# Note Permission is already wrapped in Depends()
Permission = configure_permissions(get_active_principals)
