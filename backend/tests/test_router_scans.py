# backend/tests/test_router_scans.py
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from models import Base, ScanJob
from main import app
from database import get_db

@pytest.fixture
def client_with_db():
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

def test_list_scan_jobs_empty(client_with_db):
    response = client_with_db.get("/api/scans")
    assert response.status_code == 200
    assert response.json() == []

def test_trigger_scan(client_with_db):
    mock_job = MagicMock()
    mock_job.id = 1
    mock_job.mode = "heuristic"
    mock_job.status = "complete"
    mock_job.articles_scanned = 5
    mock_job.articles_flagged = 2
    mock_job.started_at = None
    mock_job.completed_at = None
    mock_job.error = None
    with patch("routers.scans.run_scan_job", return_value=mock_job):
        response = client_with_db.post("/api/scans/trigger", json={"mode": "heuristic"})
    assert response.status_code == 200
