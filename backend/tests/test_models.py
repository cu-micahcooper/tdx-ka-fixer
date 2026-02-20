# backend/tests/test_models.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from models import Base, Article, AnalysisResult, ReviewQueue, ApprovedChange, AuditLog, ScanJob

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_article_create(db):
    article = Article(
        tdx_id=101,
        title="Test Article",
        body="Some content",
        category_id=1,
        category_name="General",
        heuristic_score=7.5,
        status="active",
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    assert article.id is not None
    assert article.title == "Test Article"

def test_analysis_result_links_to_article(db):
    article = Article(tdx_id=102, title="Art", body="Body",
                      category_id=1, category_name="Cat",
                      heuristic_score=4.0, status="active")
    db.add(article)
    db.commit()
    result = AnalysisResult(
        article_id=article.id,
        model_used="claude-sonnet-4-6",
        score_clarity=7.0, score_completeness=6.0,
        score_findability=5.0, score_redundancy=8.0, score_accuracy=7.0,
        overall_score=6.6,
        issue_summary="Needs work",
        defects_json="[]",
        proposed_body="Better body",
        approval_tier="confirm",
    )
    db.add(result)
    db.commit()
    assert result.article_id == article.id

def test_review_queue_links_to_article_and_analysis(db):
    article = Article(tdx_id=103, title="Art", body="Body",
                      category_id=1, category_name="Cat",
                      heuristic_score=4.0, status="active")
    db.add(article)
    db.flush()
    analysis = AnalysisResult(
        article_id=article.id, model_used="test",
        score_clarity=6.0, score_completeness=6.0, score_findability=6.0,
        score_redundancy=6.0, score_accuracy=6.0, overall_score=6.0,
        issue_summary="Issues", defects_json="[]",
        proposed_body="Better", approval_tier="confirm",
    )
    db.add(analysis)
    db.flush()
    qi = ReviewQueue(article_id=article.id, analysis_id=analysis.id)
    db.add(qi)
    db.commit()
    assert qi.status == "pending"
    assert qi.article_id == article.id

def test_scan_job_create(db):
    job = ScanJob(mode="heuristic", articles_scanned=10, articles_flagged=3, status="complete")
    db.add(job)
    db.commit()
    assert job.id is not None
    assert job.mode == "heuristic"
