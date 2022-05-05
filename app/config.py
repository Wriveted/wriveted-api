from functools import lru_cache
from typing import Any, Dict, List, Optional, Union

from pydantic import AnyHttpUrl, AnyUrl, BaseSettings, DirectoryPath, validator


class Settings(BaseSettings):
    API_V1_STR: str = "/v1"

    FIREBASE_PROJECT_ID: str = "wriveted-api"

    # # TODO these should be optional, we could support deployment on AWS (e.g. RDS + Fargate)
    # # GCP specific configuration
    GCP_PROJECT_ID: str = "wriveted-api"
    GCP_CLOUD_SQL_INSTANCE_ID: str = "wriveted"
    GCP_LOCATION: str = "australia-southeast1"

    POSTGRESQL_DATABASE_SOCKET_PATH: Optional[DirectoryPath]  # e.g. /cloudsql

    POSTGRESQL_SERVER: str = "/"
    POSTGRESQL_DATABASE: str = "postgres"
    POSTGRESQL_USER: str = "postgres"
    POSTGRESQL_PASSWORD: str

    SQLALCHEMY_DATABASE_URI: str = None

    @validator("SQLALCHEMY_DATABASE_URI", pre=True)
    def assemble_sqlalchemy_connection(
        cls, v: Optional[str], values: Dict[str, Any]
    ) -> Any:
        if isinstance(v, str):
            # If a string is provided (e.g. via environment variable) we just use that
            return v

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

        return AnyUrl.build(
            scheme="postgresql",
            user=db_user,
            password=db_password,
            host=db_host,
            path=db_name,
            query=query,
        )

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
        # Firebase URLs
        "https://wriveted-library.web.app",
        "https://wriveted-api.web.app",
        # Production Cloud Run Deployments - Direct URLs
        "https://wriveted-api-lg5ntws4da-ts.a.run.app",
        "https://wriveted-admin-ui-lg5ntws4da-ts.a.run.app",
        # Non Prod Cloud Run Deployment - Direct URLs
        "https://wriveted-api--nonprod-main-3glz1j0b.web.app",
        # Landbot
        "http://34.77.31.159",
        "http://23.251.142.192",
        # TypeBot
        "https://typebot.io",
        "http://13.38.101.232"
    ]

    @validator("BACKEND_CORS_ORIGINS", pre=True)
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

    DEBUG: bool = False

    class Config:
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
