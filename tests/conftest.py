import pytest
from fastapi.testclient import TestClient
from ku_gateway.main import app

@pytest.fixture
def client():
    return TestClient(app)