# backend/tests/test_router_queue.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from models import Base, Article, AnalysisResult, ReviewQueue
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
        art = Article(tdx_id=1, title="Art", body="Old",
                      category_id=1, category_name="Cat",
                      heuristic_score=4.0, status="active")
        s.add(art)
        s.flush()
        ana = AnalysisResult(
            article_id=art.id, model_used="test",
            score_clarity=6.0, score_completeness=6.0,
            score_findability=6.0, score_redundancy=6.0, score_accuracy=6.0,
            overall_score=6.0, issue_summary="Issues", defects_json="[]",
            proposed_body="Better", approval_tier="confirm",
        )
        s.add(ana)
        s.flush()
        s.add(ReviewQueue(article_id=art.id, analysis_id=ana.id))
        s.commit()
    yield TestClient(app)
    app.dependency_overrides.clear()

def test_list_queue(client_with_db):
    response = client_with_db.get("/api/queue")
    assert response.status_code == 200
    assert len(response.json()) == 1

def test_approve_queue_item(client_with_db):
    response = client_with_db.post("/api/queue/1/approve")
    assert response.status_code == 200
    assert response.json()["status"] == "approved"

def test_reject_queue_item(client_with_db):
    response = client_with_db.post("/api/queue/1/reject",
                                   json={"note": "Not needed"})
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"

def test_skip_queue_item(client_with_db):
    response = client_with_db.post("/api/queue/1/skip")
    assert response.status_code == 200
    assert response.json()["status"] == "skipped"
