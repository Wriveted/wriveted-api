from pydantic import BaseSettings


class Settings(BaseSettings):
    WRIVETED_API: str = "https://api.wriveted.com"

    # This can be a service account or user account token
    WRIVETED_API_TOKEN: str

    NZ_SCHOOL_DATA_URL: str = (
        "https://catalogue.data.govt.nz/dataset/c1923d33-e781-46c9-9ea1-d9b850082be4/resource/20b7c271-fd5a-4c9e-869b-481a0e2453cd/download/schooldirectory-09-03-2023-083055.csv"
    )


settings = Settings()
