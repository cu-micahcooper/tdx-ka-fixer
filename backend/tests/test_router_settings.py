# backend/tests/test_router_settings.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from models import Base
from main import app
from database import get_db


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    def override_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_get_settings_seeds_defaults(client):
    """First GET creates a row and returns non-empty defaults."""
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert "internal_directive" in data
    assert "public_directive" in data
    # Defaults should be pre-populated with Cedarville context
    assert len(data["internal_directive"]) > 50
    assert len(data["public_directive"]) > 50


def test_get_settings_is_idempotent(client):
    """Two GETs return identical data and don't create duplicate rows."""
    r1 = client.get("/api/settings")
    r2 = client.get("/api/settings")
    assert r1.json() == r2.json()


def test_patch_settings_updates_directives(client):
    client.get("/api/settings")  # seed
    response = client.patch(
        "/api/settings",
        json={"internal_directive": "Internal only text"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["internal_directive"] == "Internal only text"
    # public_directive unchanged
    assert len(data["public_directive"]) > 50


def test_patch_then_get_persists(client):
    client.get("/api/settings")  # seed
    client.patch("/api/settings", json={"public_directive": "Public text"})
    response = client.get("/api/settings")
    assert response.json()["public_directive"] == "Public text"


def test_patch_empty_string_allowed(client):
    client.get("/api/settings")
    response = client.patch("/api/settings", json={"internal_directive": ""})
    assert response.status_code == 200
    assert response.json()["internal_directive"] == ""
