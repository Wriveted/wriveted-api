import textwrap
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from starlette import status
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from structlog import get_logger
from structlog.contextvars import bind_contextvars, clear_contextvars

from app.api import api_router
from app.config import get_settings
from app.logging import init_logging

api_docs = textwrap.dedent(
    """
# 🤖 

Welcome human to a brief outline of the Wriveted API. 

Use this API to add, edit, and remove information about Users, Books, Schools
and Libraries.

The API is designed for use by multiple users:
- **Library Management Systems**. In particular see the section on 
  updating and setting Schools collections.
- **Wriveted Staff** either directly via scripts or via an admin UI.
- **Huey** chatbot

Note all requests require credentials, with the exceptions of getting public information on 
schools, the application version, and the security policy.

## 🔐 Authentication

The good news is that as an API user you just need to send an access token
in the `Authorization` header and all endpoints should *just work*. The
notable exception being the `/auth/firebase` endpoint which exchanges a firebase
SSO token for a Wriveted API Access Token.

As a LMS integrator or developer your access token will be provided to you by the 
Wriveted team.

You can check it by calling the `GET /auth/me` endpoint.

## 🚨 Authorization

The API implements role based access control, only particular roles are allowed
to add new schools or edit collections.

"""
)

settings = get_settings()
init_logging(settings)
logger = get_logger()
logger.info("Starting Wriveted API")

app = FastAPI(
    title="Wriveted API",
    description=api_docs,
    docs_url="/v1/docs",
    redoc_url="/v1/redoc",
    debug=settings.DEBUG,
    # version=metadata.version("wriveted-api"),
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logger.warning(
        f"The client sent invalid data!: {exc}\n\n{exc.errors()}",
        request=request.url,
    )
    return await request_validation_exception_handler(request, exc)


async def catch_exceptions_middleware(request: Request, call_next):
    """
    This global middleware allows us to log any unexpected exceptions and ensure
    we don't return any unsanitized output to clients.
    """
    try:
        return await call_next(request)
    except HTTPException as e:
        # This exception is assumed fine for end users
        raise e
    except Exception as e:
        logger.error(
            "An uncaught exception occurred in a request handler",
            request=request.url,
            method=request.method,
            exc_info=e,
        )
        return Response(
            "Internal server error", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Note without this handler being added before the CORS middleware, internal errors
# don't include CORS headers - which masks the underlying internal error as a CORS error
# to clients.
app.middleware("http")(catch_exceptions_middleware)
# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    logger.info(
        "Enabling cross origin restrictions",
        cors_origins=[str(c) for c in settings.BACKEND_CORS_ORIGINS],
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        # allow preview channels from library dashboard app frontend
        allow_origin_regex="(https:\/\/wriveted.*web\.app)|(https:\/\/huey-books.*web\.app)",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    """
    Middleware to add a UUID to each request.

    Adds a header to the response `X-Request-ID` with this ID.
    """
    request_id = str(uuid.uuid4())
    clear_contextvars()
    bind_contextvars(request_id=request_id, request_path=request.url.path)

    logger.debug("Request started", request_method=request.method)
    # Create a default response
    response = Response("No Content", status_code=status.HTTP_204_NO_CONTENT)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
    finally:
        logger.debug("Request ended")
        return response


app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    """
    Redirects to the OpenAPI documentation for the current version
    """
    return RedirectResponse("/v1/docs", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@app.get("/docs")
async def redirect_old_docs_route():
    """
    Redirects to the OpenAPI documentation for the current version
    """
    return RedirectResponse("/v1/docs", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
