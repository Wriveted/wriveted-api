import textwrap

from fastapi import FastAPI
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from starlette import status
from starlette.responses import RedirectResponse
from structlog import get_logger

from app.config import get_settings
from app.logging import init_logging
from app.api.internal import router as internal_api_router


api_docs = textwrap.dedent(
    """
# Wriveted Internal API 

Use this API to process long running tasks and react to non-time critical events.

## 🔐 Authentication

Same as Wriveted's public API just send an access token in the `Authorization`
header.

## ⏰ Task Queue

While this is a standard REST API, the recommended use is via GCP Cloud Tasks.

"""
)

settings = get_settings()
init_logging(settings)
logger = get_logger()

logger.info("Starting Wriveted Internal API")

internal_app = FastAPI(
    title="Wriveted Internal API",
    description=api_docs,
    docs_url="/v1/docs",
    redoc_url="/v1/redoc"
)


@internal_app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logger.warning(
        f"The client sent invalid data!: {exc}\n\n{exc.errors()}",
        request=request.url,
    )
    return await request_validation_exception_handler(request, exc)


internal_app.include_router(internal_api_router, prefix=settings.API_V1_STR)


@internal_app.get("/")
async def root():
    """
    Redirects to the OpenAPI documentation for the current version
    """
    return RedirectResponse("/v1/docs", status_code=status.HTTP_307_TEMPORARY_REDIRECT)

