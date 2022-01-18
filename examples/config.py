from pydantic import BaseSettings, AnyHttpUrl


class Settings(BaseSettings):
    WRIVETED_API: AnyHttpUrl = "http://0.0.0.0:8000"

    # This can be a service account or user account token
    WRIVETED_API_TOKEN: str


settings = Settings()
