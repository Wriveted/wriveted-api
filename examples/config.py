from pydantic import AnyHttpUrl, BaseSettings


class Settings(BaseSettings):
    WRIVETED_API: AnyHttpUrl = "http://localhost:8000/v1"

    # This can be a service account or user account token
    WRIVETED_API_TOKEN: str = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2NDY4NzA1ODcsImlhdCI6MTY0NjE3OTM4Nywic3ViIjoiV3JpdmV0ZWQ6VXNlci1BY2NvdW50OjEyZDA5Mjg4LWU5MjAtNGFkMS04NmQzLTEyNTdjNGFhZGExMCJ9.eXY6w7x--x1OmOwPXVozzMQbIx01qEIY3oa0vJoS6Oo"
    )

    NIELSEN_API: AnyHttpUrl = (
        "https://ws.nielsenbookdataonline.com/BDOLRest/RESTwebServices/BDOLrequest"
    )
    NIELSEN_CLIENT_ID: str = "WrivetedWebServices"
    NIELSEN_CLIENT_PASSWORD: str


settings = Settings()
