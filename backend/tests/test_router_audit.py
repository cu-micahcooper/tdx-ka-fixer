# backend/tests/test_router_audit.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from datetime import datetime
from models import Base, Article, AuditLog
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
    with Session(engine) as s:
        art = Article(tdx_id=10, title="Art", body="Body",
                      category_id=1, category_name="Cat",
                      heuristic_score=8.0, status="active")
        s.add(art)
        s.flush()
        s.add(AuditLog(
            article_id=art.id, tdx_id=10, action="update",
            original_body="Old", new_body="New",
            approved_at=datetime.utcnow(),
        ))
        s.commit()
    yield TestClient(app)
    app.dependency_overrides.clear()

def test_list_audit_log(client_with_db):
    response = client_with_db.get("/api/audit")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["action"] == "update"
    assert data[0]["tdx_id"] == 10
