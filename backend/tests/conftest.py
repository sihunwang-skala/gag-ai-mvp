import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

UID = "test-user-0001"


@pytest.fixture()
def client(tmp_path):
    s = Settings(llm_provider="mock", database_url=f"sqlite:///{tmp_path}/t.db")
    c = TestClient(create_app(s))
    c.headers.update({"X-Demo-User": UID})
    return c
