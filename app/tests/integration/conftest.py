import pytest
from starlette.testclient import TestClient


@pytest.fixture(scope="module")
def app():
    app = create_app()
    yield app
