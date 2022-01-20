from app.fastapi_application import create_application
from app.config import get_settings


config = get_settings()
app = create_application(config)

