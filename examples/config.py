from pydantic import BaseSettings, AnyHttpUrl


class Settings(BaseSettings):
    WRIVETED_API: AnyHttpUrl = "http://localhost:8000/v1"

    # This can be a service account or user account token
    WRIVETED_API_TOKEN: str

    NIELSEN_API: AnyHttpUrl = (
        "https://ws.nielsenbookdataonline.com/BDOLRest/RESTwebServices/BDOLrequest"
    )
    NIELSEN_CLIENT_ID: str
    NIELSEN_CLIENT_PASSWORD: str


settings = Settings()
