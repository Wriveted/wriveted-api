import uuid

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from starlette.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db.session import get_session
from app.models import Work, Author, Series, Edition

from app.api.version import router as version_router
from app.api.editions import router as edition_router
from app.api.works import router as work_router
from app.api.schools import router as school_router
from app.api.authors import router as author_router
from app.api.illustrators import router as illustrator_router
from app.api.collections import router as collections_router
from app.api.auth import router as auth_router
from app.api.users import router as user_router
from app.api.service_accounts import router as service_account_router

settings = get_settings()
app = FastAPI(
    title="Wriveted API"
)

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(author_router)
app.include_router(illustrator_router)
app.include_router(edition_router)
app.include_router(school_router)
app.include_router(work_router)
app.include_router(collections_router)
app.include_router(service_account_router)
app.include_router(version_router)



@app.get("/")
async def root(session: Session = Depends(get_session),):
    config = get_settings()

    return {
        "message": "Hello World",
        "config": config,
    }

