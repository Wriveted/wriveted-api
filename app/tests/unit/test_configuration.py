import pytest

from app.config import Settings


def test_pass():
    assert True


pytest.mark.xfail("This should fail")
def test_fail():
    assert True


def test_can_create_settings():
    config = Settings(POSTGRESQL_PASSWORD='test', SECRET_KEY='test')
    assert hasattr(config, "SECRET_KEY")
