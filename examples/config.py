from pydantic import BaseSettings, AnyHttpUrl


class Settings(BaseSettings):
    WRIVETED_API: AnyHttpUrl = "http://localhost:8000/v1"

    # This can be a service account or user account token
    WRIVETED_API_TOKEN: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2NDM5NDM5NjQsImlhdCI6MTY0MzI1Mjc2NCwic3ViIjoid3JpdmV0ZWQ6dXNlci1hY2NvdW50OjlhODY4ZDliLTEzNDktNDhlYi05NDRmLTMxZTg3MWNkNGM3NyJ9.ZX-Hek_XrqhotN-CxLe4uVzw365xwKEtEzf7-9JHQBE"

    NIELSEN_API: AnyHttpUrl      = "https://ws.nielsenbookdataonline.com/BDOLRest/RESTwebServices/BDOLrequest"
    NIELSEN_CLIENT_ID: str
    NIELSEN_CLIENT_PASSWORD: str


settings = Settings()