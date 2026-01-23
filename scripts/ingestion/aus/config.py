from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    WRIVETED_API: str = "https://api.wriveted.com"  # Production by default

    # This can be a service account or user account token
    WRIVETED_API_TOKEN: str


@lru_cache
def get_settings() -> Settings:
    return Settings()


# For backward compatibility with existing scripts
class _LazySettings:
    def __getattr__(self, name: str):
        return getattr(get_settings(), name)


settings = _LazySettings()
