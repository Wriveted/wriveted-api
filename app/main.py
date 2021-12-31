import textwrap
import uuid

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from starlette import status
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse

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


api_docs = textwrap.dedent("""
# 🤖 

Welcome human to a brief outline of the Wriveted API. 

Use this API to add, edit, and remove information about Users, Books, Schools
and Libraries.

The API is designed for use by multiple users:
- **Library Management Systems**. In particular see the section on 
  updating and setting Schools collections.
- **Wriveted Staff** either directly via scripts or via an admin UI.
- **Huey** chatbot (eventually)

Note all requests require credentials.

## 🔐 Authentication

The good news is that you as an API user should just need to send an access token
in the `Authorization` header and all endpoints should *just work*. The
notable exception being the `/auth/firebase` endpoint which exchanges a firebase
token for a Wriveted API Access Token.

As a developer your access token will be provided to you by the Wriveted team.

You can check it by calling the `GET /auth/me` endpoint.

## 🚨 Authorization

The API implements role based access control, only particular roles are allowed
to add new schools or edit collections.


""")

settings = get_settings()
app = FastAPI(
    title="Wriveted API",
    description=api_docs,

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
async def root():
    return RedirectResponse('/docs',
                            status_code=status.HTTP_307_TEMPORARY_REDIRECT)

