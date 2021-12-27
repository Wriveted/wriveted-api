import pydantic
from pydantic import BaseSettings


class Settings(BaseSettings):
    WRIVETED_API: str = "http://localhost:8000"


settings = Settings()