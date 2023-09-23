import enum
from functools import lru_cache
from typing import Any, List, Optional, Union

from pydantic import AnyHttpUrl, DirectoryPath, HttpUrl, field_validator
from pydantic_core.core_schema import FieldValidationInfo
from pydantic_settings import BaseSettings, SettingsConfigDict
from structlog import get_logger

logger = get_logger()


class Settings(BaseSettings):
    API_V1_STR: str = "/v1"

    FIREBASE_PROJECT_ID: str = "wriveted-api"

    # # TODO these should be optional, we could support deployment on AWS (e.g. RDS + Fargate)
    # # GCP specific configuration
    GCP_PROJECT_ID: str = "wriveted-api"
    GCP_CLOUD_SQL_INSTANCE_ID: str = "wriveted"
    GCP_LOCATION: str = "australia-southeast1"

    GCP_IMAGE_BUCKET: str = "wriveted-cover-images"
    GCP_HUEY_MEDIA_BUCKET: str = "wriveted-huey-media"
    GCP_BOOK_DATA_BUCKET: str = "wriveted-book-data"

    GCP_CLOUD_TASKS_NAME: Optional[str] = None  # 'background-tasks'
    GCP_CLOUD_TASKS_SERVICE_ACCOUNT: str = (
        "background-tasks@wriveted-api.iam.gserviceaccount.com"
    )
    WRIVETED_INTERNAL_API: Optional[AnyHttpUrl] = None

    POSTGRESQL_DATABASE_SOCKET_PATH: Optional[DirectoryPath] = None  # e.g. /cloudsql

    POSTGRESQL_SERVER: str = "/"
    POSTGRESQL_DATABASE: str = "postgres"
    POSTGRESQL_USER: str = "postgres"
    POSTGRESQL_PASSWORD: str

    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 10

    SENDGRID_API_KEY: str

    SHOPIFY_HMAC_SECRET: str

    OPENAI_API_KEY: str = ""
    # See https://platform.openai.com/docs/models/model-endpoint-compatibility
    # e.g. "gpt-3.5-turbo", "gpt-4"
    OPENAI_MODEL: str = "gpt-4"
    OPENAI_TIMEOUT: float = 60.0

    LABEL_AFTER_HYDRATION: bool = True

    GPT_SERVICE_ACCOUNT_ID: str = "2c092595-76e8-4ba9-9340-37b7237d6b59"

    SLACK_BOT_TOKEN: str = ""

    HUEY_BOOKS_APP_URL: str = "https://hueybooks.com"

    NIELSEN_API_URL: str = (
        "https://ws.nielsenbookdataonline.com/BDOLRest/RESTwebServices/BDOLrequest"
    )
    NIELSEN_CLIENT_ID: str = "WrivetedWebServices"
    NIELSEN_PASSWORD: str = ""
    NIELSEN_ENABLE_CACHE: bool = False
    NIELSEN_CACHE_RESULTS: bool = True

    SQLALCHEMY_DATABASE_URI: str | None = None

    @field_validator("SQLALCHEMY_DATABASE_URI", mode="before")
    @classmethod
    def assemble_sqlalchemy_connection(
        cls, v: Optional[str], info: FieldValidationInfo
    ) -> Any:
        if isinstance(v, str):
            # If a string is provided (e.g. via environment variable) we just use that
            return v

        values = info.data
        # Otherwise, assemble a sqlalchemy connection string from the other provided values.
        db_host = values.get("POSTGRESQL_SERVER")
        db_user = values.get("POSTGRESQL_USER")
        db_password = values.get("POSTGRESQL_PASSWORD")
        db_name = values.get("POSTGRESQL_DATABASE")

        query = None
        # Connect to Cloud SQL using unix socket instead of TCP socket
        # https://cloud.google.com/sql/docs/postgres/connect-run?authuser=1#connecting_to
        socket_path = values.get("POSTGRESQL_DATABASE_SOCKET_PATH")

        if socket_path is not None:
            project = values.get("GCP_PROJECT_ID")
            location = values.get("GCP_LOCATION")
            cloud_sql_instance_id = values.get("GCP_CLOUD_SQL_INSTANCE_ID")
            cloud_sql_instance_connection = (
                f"{project}:{location}:{cloud_sql_instance_id}"
            )
            query = f"host={socket_path}/{cloud_sql_instance_connection}"

        scheme = "postgresql"

        # Assemble it all together:
        connection_string = (
            f"{scheme}://{db_user}:{db_password}@{db_host}/{db_name}?{query}"
        )
        logger.debug(f"Connection string {connection_string}")
        return connection_string

    # BACKEND_CORS_ORIGINS is a JSON-formatted list of allowed request origins
    # e.g: '["http://localhost", "http://localhost:4200", "http://localhost:3000", \
    # "http://localhost:8080", "http://actual.domain.com"]'
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = [
        # Local development URLs
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        # Production URLs
        "https://api.wriveted.com",
        "https://bookbot.hellohuey.com",
        "https://app.hueythebookbot.com",
        "https://api.hueythebookbot.com",
        "https://www.hueythebookbot.com",
        # Huey Books Production URLs
        "https://hueybooks.com",
        "https://www.hueybooks.com",
        # Firebase URLs
        "https://wriveted-library.web.app",
        "https://wriveted-api.web.app",
        "https://huey-books.web.app",
        # Production Cloud Run Deployments - Direct URLs
        "https://wriveted-api-lg5ntws4da-ts.a.run.app",
        "https://wriveted-admin-ui-lg5ntws4da-ts.a.run.app",
        # Non Prod Cloud Run Deployment - Direct URLs
        "https://wriveted-api--nonprod-main-3glz1j0b.web.app",
        # Landbot
        "http://34.77.31.159",
        "http://23.251.142.192",
        "https://chats.landbot.io",
        "https://landbot.site",
        "https://landbot.pro",
        # TypeBot
        "https://typebot.io",
        "http://13.38.101.232",
        "http://15.188.52.37",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # This must be set for JWT token to persist and be valid between multiple
    # API processes create with `secrets.token_urlsafe(32)`
    SECRET_KEY: str

    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8

    # 2 years
    SERVICE_ACCOUNT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 365 * 2

    class LoggingLevel(str, enum.Enum):
        DEBUG = "DEBUG"
        INFO = "INFO"
        WARNING = "WARNING"

    LOGGING_LEVEL: LoggingLevel = LoggingLevel.INFO
    AUTH_LOGGING_LEVEL: LoggingLevel = LoggingLevel.INFO

    METABASE_SITE_URL: HttpUrl = "https://metabase-lg5ntws4da-ts.a.run.app"
    METABASE_SECRET_KEY: str = ""

    # Capture uvicorn's access log messages in our logging stack
    LOG_UVICORN_ACCESS: bool = True
    LOG_AS_JSON: bool = False
    DEBUG: bool = False

    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    model_config = SettingsConfigDict(case_sensitive=True, use_enum_values=True)


@lru_cache()
def get_settings() -> Settings:
    return Settings()
