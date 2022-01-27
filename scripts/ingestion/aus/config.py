from pydantic import BaseSettings


class Settings(BaseSettings):
    WRIVETED_API: str = "https://api.wriveted.com"

    # This can be a service account or user account token
    WRIVETED_API_TOKEN: str


settings = Settings()
