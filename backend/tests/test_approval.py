# backend/tests/test_approval.py
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from models import Base, Article, AnalysisResult, ReviewQueue, ApprovedChange
from services.approval import ApprovalService

@pytest.fixture
def db():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    with Session(eng) as session:
        yield session

def seed_queue_item(db, tier="confirm"):
    article = Article(tdx_id=99, title="Art", body="Original body",
                      category_id=1, category_name="Cat",
                      heuristic_score=4.0, status="active")
    db.add(article)
    db.flush()
    analysis = AnalysisResult(
        article_id=article.id, model_used="test",
        score_clarity=7.0, score_completeness=7.0, score_findability=7.0,
        score_redundancy=7.0, score_accuracy=7.0, overall_score=7.0,
        issue_summary="Minor issues", defects_json="[]",
        proposed_body="Improved body", approval_tier=tier,
    )
    db.add(analysis)
    db.flush()
    qi = ReviewQueue(article_id=article.id, analysis_id=analysis.id)
    db.add(qi)
    db.commit()
    return qi

def test_approve_creates_approved_change(db):
    qi = seed_queue_item(db)
    svc = ApprovalService(db=db)
    svc.approve(queue_item_id=qi.id)
    db.refresh(qi)
    assert qi.status == "approved"
    change = db.query(ApprovedChange).filter_by(review_queue_id=qi.id).first()
    assert change is not None
    assert change.approved_body == "Improved body"
    assert change.original_body == "Original body"

def test_approve_with_edit_uses_edited_body(db):
    qi = seed_queue_item(db)
    svc = ApprovalService(db=db)
    svc.approve(queue_item_id=qi.id, edited_body="Manually edited body")
    change = db.query(ApprovedChange).filter_by(review_queue_id=qi.id).first()
    assert change.approved_body == "Manually edited body"

def test_reject_updates_status(db):
    qi = seed_queue_item(db)
    svc = ApprovalService(db=db)
    svc.reject(queue_item_id=qi.id, note="Not relevant")
    db.refresh(qi)
    assert qi.status == "rejected"
    assert qi.reviewer_note == "Not relevant"

def test_skip_updates_status(db):
    qi = seed_queue_item(db)
    svc = ApprovalService(db=db)
    svc.skip(queue_item_id=qi.id)
    db.refresh(qi)
    assert qi.status == "skipped"

def test_approve_raises_on_missing_item(db):
    svc = ApprovalService(db=db)
    with pytest.raises(ValueError, match="not found"):
        svc.approve(queue_item_id=9999)
