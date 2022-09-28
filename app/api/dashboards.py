import datetime

from fastapi import APIRouter, Depends
from jose import jwt
from pydantic import BaseModel, HttpUrl

from app.api.dependencies.security import get_current_active_superuser_or_backend_service_account
from app.config import get_settings

router = APIRouter(
    tags=["Security"],
    dependencies=[Depends(get_current_active_superuser_or_backend_service_account)]
)
config = get_settings()


class DashboardLink(BaseModel):
    url: HttpUrl


@router.get("/dashboard/kpi", response_model=DashboardLink)
def get_kpi_dashboard():
    dashboard_id = 5

    return {
        "url": get_metabase_dashboard_embed_link(dashboard_id)
    }


def get_metabase_dashboard_embed_link(dashboard_id):
    payload = {
        "resource": {"dashboard": dashboard_id},
        "params": {},
        "exp": datetime.timedelta(minutes=10).total_seconds()
    }
    token = jwt.encode(payload, config.METABASE_SECRET_KEY)
    url = f"{config.METABASE_SITE_URL}/embed/dashboard/{token}#bordered=true&titled=true"
    return url

