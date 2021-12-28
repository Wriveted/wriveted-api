import secrets
from functools import lru_cache
from typing import List, Optional, Union, Dict, Any

from pydantic import AnyHttpUrl, BaseSettings, SecretStr, validator, FilePath, DirectoryPath, AnyUrl


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"

    GOOGLE_PROJECT_ID: str = "hardbyte-wriveted-development"
    FIREBASE_PROJECT_ID: str = "hardbyte-wriveted-development"

    GOOGLE_SQL_INSTANCE_ID: str = "wriveted"
    GOOGLE_SQL_DATABASE_ID: str = "alembic-test"
    GOOGLE_SQL_DATABASE_PASSWORD: str = "gJduFxMylJN1v44B"

    SQLALCHEMY_DATABASE_URI: str = None

    @validator("SQLALCHEMY_DATABASE_URI", pre=True)
    def assemble_sqlalchemy_connection(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
        if isinstance(v, str):
            # If a string is provided (e.g. via environment variable) we just use that
            return v
        project_id = values.get("GOOGLE_PROJECT_ID")
        cloud_sql_instance_id = values.get("GOOGLE_SQL_INSTANCE_ID")
        cloud_sql_db_id = values.get("GOOGLE_SQL_DATABASE_ID")

        path = f"projects/{project_id}/instances/{cloud_sql_instance_id}/databases/{cloud_sql_db_id}"

        return AnyUrl.build(
            scheme="postgresql",
            host="/",
            path=path,
        )

    # BACKEND_CORS_ORIGINS is a JSON-formatted list of origins
    # e.g: '["http://localhost", "http://localhost:4200", "http://localhost:3000", \
    # "http://localhost:8080", "http://actual.domain.com"]'
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = ["http://localhost:3000", "http://localhost:8000"]

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # This must be set for JWT token to persist and be valid between multiple
    # API processes create with `secrets.token_urlsafe(32)`
    SECRET_KEY: str = 'CjZNhAWKT7hrkqiEpnXgGCkgYk2O5mXKePFML-1iC8M'

    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8

    class Config:
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


