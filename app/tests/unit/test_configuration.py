from app.config import Settings


def test_can_create_settings():
    config = Settings(POSTGRESQL_PASSWORD="test", SECRET_KEY="test")
    assert hasattr(config, "SECRET_KEY")
