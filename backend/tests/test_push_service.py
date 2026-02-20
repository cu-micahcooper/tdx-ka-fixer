# backend/tests/test_push_service.py
import pytest
from datetime import datetime
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from models import Base, Article, AnalysisResult, ReviewQueue, ApprovedChange, AuditLog
from services.push_service import PushService

@pytest.fixture
def db():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    with Session(eng) as session:
        yield session

def seed_approved_change(db):
    article = Article(tdx_id=55, title="Art", body="Old body",
                      category_id=1, category_name="Cat",
                      heuristic_score=4.0, status="active")
    db.add(article)
    db.flush()
    analysis = AnalysisResult(
        article_id=article.id, model_used="test",
        score_clarity=8.0, score_completeness=8.0, score_findability=8.0,
        score_redundancy=8.0, score_accuracy=8.0, overall_score=8.0,
        issue_summary="Good", defects_json="[]",
        proposed_body="New body", approval_tier="confirm",
    )
    db.add(analysis)
    db.flush()
    qi = ReviewQueue(article_id=article.id, analysis_id=analysis.id, status="approved")
    db.add(qi)
    db.flush()
    change = ApprovedChange(
        review_queue_id=qi.id, article_id=article.id,
        original_body="Old body", approved_body="New body",
    )
    db.add(change)
    db.commit()
    return change

def test_push_calls_tdx_update(db):
    change = seed_approved_change(db)
    tdx = MagicMock()
    tdx.update_article.return_value = {"Body": "New body"}
    svc = PushService(db=db, tdx_client=tdx)
    svc.push(change.id)
    tdx.update_article.assert_called_once_with(55, "New body")

def test_push_writes_audit_log(db):
    change = seed_approved_change(db)
    tdx = MagicMock()
    tdx.update_article.return_value = {"Body": "New body"}
    svc = PushService(db=db, tdx_client=tdx)
    svc.push(change.id)
    log = db.query(AuditLog).first()
    assert log is not None
    assert log.tdx_id == 55
    assert log.new_body == "New body"
    assert log.action == "update"

def test_push_updates_article_body_in_db(db):
    change = seed_approved_change(db)
    tdx = MagicMock()
    tdx.update_article.return_value = {"Body": "New body"}
    svc = PushService(db=db, tdx_client=tdx)
    svc.push(change.id)
    article = db.query(Article).filter_by(tdx_id=55).first()
    assert article.body == "New body"

def test_push_marks_failed_on_tdx_error(db):
    change = seed_approved_change(db)
    tdx = MagicMock()
    tdx.update_article.side_effect = RuntimeError("TDX unavailable")
    svc = PushService(db=db, tdx_client=tdx)
    with pytest.raises(RuntimeError):
        svc.push(change.id)
    db.refresh(change)
    assert change.push_status == "failed"
    assert "TDX unavailable" in change.push_error

def test_push_all_pending_continues_after_failure(db):
    # Seed two approved changes
    change1 = seed_approved_change(db)
    # Seed a second one with a different tdx_id
    article2 = Article(tdx_id=56, title="Art2", body="Old body 2",
                       category_id=1, category_name="Cat",
                       heuristic_score=4.0, status="active")
    db.add(article2)
    db.flush()
    analysis2 = AnalysisResult(
        article_id=article2.id, model_used="test",
        score_clarity=8.0, score_completeness=8.0, score_findability=8.0,
        score_redundancy=8.0, score_accuracy=8.0, overall_score=8.0,
        issue_summary="Good", defects_json="[]",
        proposed_body="New body 2", approval_tier="confirm",
    )
    db.add(analysis2)
    db.flush()
    qi2 = ReviewQueue(article_id=article2.id, analysis_id=analysis2.id, status="approved")
    db.add(qi2)
    db.flush()
    change2 = ApprovedChange(
        review_queue_id=qi2.id, article_id=article2.id,
        original_body="Old body 2", approved_body="New body 2",
    )
    db.add(change2)
    db.commit()

    tdx = MagicMock()
    # First call fails, second succeeds
    tdx.update_article.side_effect = [RuntimeError("fail"), {"Body": "New body 2"}]
    svc = PushService(db=db, tdx_client=tdx)
    results = svc.push_all_pending()

    assert len(results) == 1  # only 1 succeeded
    db.refresh(change1)
    db.refresh(change2)
    assert change1.push_status == "failed"
    assert change2.push_status == "success"
