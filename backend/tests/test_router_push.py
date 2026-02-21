# backend/tests/test_router_push.py
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from models import Base, Article, AnalysisResult, ReviewQueue, ApprovedChange
from main import app
from database import get_db
import routers.push as push_router


def make_engine():
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def seed_approved_change(session):
    art = Article(
        tdx_id=99, title="Test Art", body="Original body",
        category_id=1, category_name="Cat",
        heuristic_score=4.0, status="active",
    )
    session.add(art)
    session.flush()
    ana = AnalysisResult(
        article_id=art.id, model_used="test",
        score_clarity=7.0, score_completeness=7.0,
        score_findability=7.0, score_redundancy=7.0, score_accuracy=7.0,
        overall_score=7.0, issue_summary="Issues",
        defects_json="[]", proposed_body="Better body",
        approval_tier="confirm",
    )
    session.add(ana)
    session.flush()
    qi = ReviewQueue(article_id=art.id, analysis_id=ana.id, status="approved")
    session.add(qi)
    session.flush()
    change = ApprovedChange(
        review_queue_id=qi.id, article_id=art.id,
        original_body="Original body", approved_body="Better body",
    )
    session.add(change)
    session.commit()
    return change


@pytest.fixture
def client_with_push():
    engine = make_engine()
    Base.metadata.create_all(engine)

    def override_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_db

    # Inject a mock push_service_factory that uses the in-memory DB
    tdx = MagicMock()
    tdx.update_article.return_value = {"Body": "Better body"}

    from services.push_service import PushService

    push_router.push_service_factory = lambda db: PushService(db=db, tdx_client=tdx)

    with Session(engine) as s:
        seed_approved_change(s)

    yield TestClient(app)

    app.dependency_overrides.clear()
    push_router.push_service_factory = None


def test_push_all_returns_200(client_with_push):
    response = client_with_push.post("/api/approved/push-all")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1


def test_push_one_returns_200_with_record(client_with_push):
    response = client_with_push.post("/api/approved/1/push")
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["push_status"] == "success"
    assert data["approved_body"] == "Better body"


def test_push_one_returns_404_when_not_found(client_with_push):
    response = client_with_push.post("/api/approved/9999/push")
    assert response.status_code == 404
