from typing import Any


from structlog import get_logger

from app.crud import CRUDBase
from app.models import ServiceAccount

from app.schemas.service_account import ServiceAccountCreateIn

logger = get_logger()


class CRUDServiceAccount(CRUDBase[ServiceAccount, ServiceAccountCreateIn, Any]):
    pass


service_account = CRUDServiceAccount(ServiceAccount)
