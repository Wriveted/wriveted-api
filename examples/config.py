import pydantic
from pydantic import BaseSettings


class Settings(BaseSettings):
    WRIVETED_API: str = "http://0.0.0.0:8000"

    # This can be a service account or user account token
    WRIVETED_API_TOKEN: str


settings = Settings()