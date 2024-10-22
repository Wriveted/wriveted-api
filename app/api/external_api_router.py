from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.authors import router as author_router
from app.api.booklists import public_router as booklist_router_public
from app.api.booklists import router as booklist_router
from app.api.classes import router as class_group_router
from app.api.collections import router as collections_router
from app.api.commerce import router as commerce_router
from app.api.dashboards import router as dashboard_router
from app.api.editions import router as edition_router
from app.api.events import router as events_router
from app.api.hydration import router as hydration_router
from app.api.illustrators import router as illustrator_router
from app.api.labelset import router as labelset_router
from app.api.recommendations import router as recommendations_router
from app.api.schools import public_router as school_router_public
from app.api.schools import router as school_router
from app.api.search import router as search_router
from app.api.service_accounts import router as service_account_router
from app.api.supporters import router as supporter_router
from app.api.users import router as user_router
from app.api.version import router as version_router
from app.api.works import router as work_router

api_router = APIRouter()


api_router.include_router(auth_router)
api_router.include_router(user_router)
api_router.include_router(author_router)
api_router.include_router(booklist_router)
api_router.include_router(booklist_router_public)
api_router.include_router(class_group_router)
api_router.include_router(collections_router)
api_router.include_router(commerce_router)
api_router.include_router(dashboard_router)
api_router.include_router(edition_router)
api_router.include_router(events_router)
api_router.include_router(hydration_router)
api_router.include_router(illustrator_router)
api_router.include_router(labelset_router)
api_router.include_router(school_router)
api_router.include_router(school_router_public)
api_router.include_router(service_account_router)
api_router.include_router(supporter_router)
api_router.include_router(version_router)
api_router.include_router(work_router)
api_router.include_router(recommendations_router)
api_router.include_router(search_router)
