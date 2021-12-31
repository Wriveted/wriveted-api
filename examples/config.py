import pydantic
from pydantic import BaseSettings


class Settings(BaseSettings):
    WRIVETED_API: str = "http://0.0.0.0:8000"


settings = Settings()