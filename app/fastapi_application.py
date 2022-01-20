
import textwrap
from fastapi import FastAPI, HTTPException
from starlette import status
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response
from structlog import get_logger
from app.api import api_router
from app.config import get_settings, Settings

logger = get_logger()
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

Note all requests require credentials, with the exceptions of getting the application
version and security policy.

## 🔐 Authentication

The good news is that as an API user should just need to send an access token
in the `Authorization` header and all endpoints should *just work*. The
notable exception being the `/auth/firebase` endpoint which exchanges a firebase
SSO token for a Wriveted API Access Token.

As a developer your access token will be provided to you by the Wriveted team.

You can check it by calling the `GET /auth/me` endpoint.

## 🚨 Authorization

The API implements role based access control, only particular roles are allowed
to add new schools or edit collections.


""")



def create_application(settings: Settings):

    app = FastAPI(
        title="Wriveted API",
        description=api_docs,
        docs_url="/v1/docs",
        redoc_url="/v1/redoc",
        debug=settings.DEBUG
    )

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
            "Enabling cross origin restrictions", cors_origins=settings.BACKEND_CORS_ORIGINS
        )
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(api_router, prefix=settings.API_V1_STR)

    @app.get("/")
    async def root():
        """
        Redirects to the OpenAPI documentation for the current version
        """
        return RedirectResponse('/v1/docs', status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    @app.get("/docs")
    async def redirect_old_docs_route():
        """
        Redirects to the OpenAPI documentation for the current version
        """
        return RedirectResponse('/v1/docs', status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    return app