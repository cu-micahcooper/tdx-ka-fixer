# backend/tests/test_scan_engine.py
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from models import Base, Article, AnalysisResult, ReviewQueue, ScanJob
from services.scan_engine import ScanEngine
from services.claude_client import AnalysisResult as ClaudeAnalysisResult

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

RAW_ARTICLE_BAD = {
    "ID": 1, "Subject": "Article 1", "Body": "TODO: fix this",
    "CategoryID": 1, "CategoryName": "Cat",
    "CreatedDate": "2023-01-01T00:00:00Z",
    "ModifiedDate": "2023-01-01T00:00:00Z",
    "NumViews": 2, "IsActive": True, "IsPublic": False,
}

RAW_ARTICLE_GOOD = {
    "ID": 2, "Subject": "Good Article", "Body": "A" * 300,
    "CategoryID": 1, "CategoryName": "Cat",
    "CreatedDate": (datetime.utcnow() - timedelta(days=10)).isoformat() + "Z",
    "ModifiedDate": (datetime.utcnow() - timedelta(days=2)).isoformat() + "Z",
    "NumViews": 50, "IsActive": True,
}

def make_mock_analyzer():
    analyzer = MagicMock()
    analyzer.model = "claude-sonnet-4-6"
    analyzer.analyze.return_value = ClaudeAnalysisResult(
        score_clarity=6.0, score_completeness=5.0, score_findability=7.0,
        score_redundancy=8.0, score_accuracy=6.0, overall_score=6.4,
        issue_summary="Needs improvement", proposed_body="Better body",
        approval_tier="confirm",
    )
    return analyzer

def test_heuristic_scan_flags_bad_article_only(db):
    tdx = MagicMock()
    tdx.list_articles.return_value = [RAW_ARTICLE_BAD, RAW_ARTICLE_GOOD]
    analyzer = make_mock_analyzer()
    engine = ScanEngine(db=db, tdx_client=tdx, analyzer=analyzer, heuristic_threshold=5.0)
    job = engine.run_heuristic_scan()
    assert job.articles_scanned == 2
    assert job.articles_flagged == 1
    assert job.status == "complete"
    # Only bad article queued
    assert db.query(ReviewQueue).count() == 1

def test_heuristic_scan_syncs_articles_to_db(db):
    tdx = MagicMock()
    tdx.list_articles.return_value = [RAW_ARTICLE_BAD]
    analyzer = make_mock_analyzer()
    engine = ScanEngine(db=db, tdx_client=tdx, analyzer=analyzer)
    engine.run_heuristic_scan()
    articles = db.query(Article).all()
    assert len(articles) == 1
    assert articles[0].tdx_id == 1
    assert articles[0].title == "Article 1"

def test_full_batch_scan_queues_all_articles(db):
    tdx = MagicMock()
    tdx.list_articles.return_value = [RAW_ARTICLE_BAD, RAW_ARTICLE_GOOD]
    analyzer = make_mock_analyzer()
    engine = ScanEngine(db=db, tdx_client=tdx, analyzer=analyzer)
    job = engine.run_full_batch_scan()
    assert job.articles_scanned == 2
    assert job.articles_flagged == 2
    assert db.query(ReviewQueue).count() == 2

def test_sync_updates_existing_article(db):
    tdx = MagicMock()
    tdx.list_articles.return_value = [RAW_ARTICLE_BAD]
    analyzer = make_mock_analyzer()
    engine = ScanEngine(db=db, tdx_client=tdx, analyzer=analyzer)
    engine.run_heuristic_scan()
    # Update title in TDX
    updated = {**RAW_ARTICLE_BAD, "Subject": "Updated Title"}
    tdx.list_articles.return_value = [updated]
    engine.run_heuristic_scan()
    articles = db.query(Article).all()
    assert len(articles) == 1  # no duplicate
    assert articles[0].title == "Updated Title"

def test_heuristic_scan_marks_job_failed_on_error(db):
    tdx = MagicMock()
    tdx.list_articles.side_effect = RuntimeError("TDX down")
    analyzer = make_mock_analyzer()
    engine = ScanEngine(db=db, tdx_client=tdx, analyzer=analyzer)
    with pytest.raises(RuntimeError):
        engine.run_heuristic_scan()
    job = db.query(ScanJob).first()
    assert job.status == "failed"
    assert "TDX down" in job.error

def test_no_duplicate_queue_entries_on_rescan(db):
    tdx = MagicMock()
    tdx.list_articles.return_value = [RAW_ARTICLE_BAD]
    analyzer = make_mock_analyzer()
    engine = ScanEngine(db=db, tdx_client=tdx, analyzer=analyzer)
    engine.run_heuristic_scan()
    engine.run_heuristic_scan()
    assert db.query(ReviewQueue).count() == 1  # no duplicate

def test_internal_article_uses_internal_directive(db):
    """Non-public articles should pass the internal_directive to analyze()."""
    from models import AppSettings
    db.add(AppSettings(internal_directive="INTERNAL DIR", public_directive="PUBLIC DIR"))
    db.commit()

    tdx = MagicMock()
    raw = {**RAW_ARTICLE_BAD, "IsPublic": False}
    tdx.list_articles.return_value = [raw]
    analyzer = make_mock_analyzer()
    engine = ScanEngine(db=db, tdx_client=tdx, analyzer=analyzer)
    engine.run_heuristic_scan()

    _, kwargs = analyzer.analyze.call_args
    assert kwargs.get("directive") == "INTERNAL DIR"


def test_public_article_uses_public_directive(db):
    """Public articles should pass the public_directive to analyze()."""
    from models import AppSettings
    db.add(AppSettings(internal_directive="INTERNAL DIR", public_directive="PUBLIC DIR"))
    db.commit()

    tdx = MagicMock()
    raw = {**RAW_ARTICLE_BAD, "IsPublic": True}
    tdx.list_articles.return_value = [raw]
    analyzer = make_mock_analyzer()
    engine = ScanEngine(db=db, tdx_client=tdx, analyzer=analyzer)
    engine.run_heuristic_scan()

    _, kwargs = analyzer.analyze.call_args
    assert kwargs.get("directive") == "PUBLIC DIR"


def test_missing_settings_row_uses_empty_directive(db):
    """If AppSettings row doesn't exist, analyze() is called with directive=''."""
    tdx = MagicMock()
    tdx.list_articles.return_value = [RAW_ARTICLE_BAD]
    analyzer = make_mock_analyzer()
    engine = ScanEngine(db=db, tdx_client=tdx, analyzer=analyzer)
    engine.run_heuristic_scan()

    _, kwargs = analyzer.analyze.call_args
    assert kwargs.get("directive") == ""


def test_full_batch_scan_flagged_count_excludes_already_queued(db):
    """articles_flagged should only count newly-queued articles, not skipped ones."""
    tdx = MagicMock()
    tdx.list_articles.return_value = [RAW_ARTICLE_BAD, RAW_ARTICLE_GOOD]
    analyzer = make_mock_analyzer()
    engine = ScanEngine(db=db, tdx_client=tdx, analyzer=analyzer)
    # First scan queues all 2 articles
    job1 = engine.run_full_batch_scan()
    assert job1.articles_flagged == 2
    assert db.query(ReviewQueue).count() == 2
    # Second scan: both already have pending entries, so flagged should be 0
    job2 = engine.run_full_batch_scan()
    assert job2.articles_flagged == 0
    assert db.query(ReviewQueue).count() == 2  # still only 2, no duplicates
