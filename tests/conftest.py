import os
import tempfile
from pathlib import Path

_temp = tempfile.TemporaryDirectory()
# Never point destructive test fixtures at a development or production database.
_test_url = os.getenv("TEST_DATABASE_URL")
if _test_url:
    from sqlalchemy.engine import make_url

    if not (make_url(_test_url).database or "").startswith("studylens_test"):
        raise RuntimeError("TEST_DATABASE_URL must use a database named studylens_test...")
os.environ["DATABASE_URL"] = _test_url or "sqlite:///" + str(Path(_temp.name) / "test.db")
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app, requests
from backend.app.database import Base, engine


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    requests.clear()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def account(client):
    response = client.post(
        "/api/auth/register", json={"email": "learner@example.com", "password": "test-password-123", "name": "Learner"}
    )
    assert response.status_code == 201
    return client
