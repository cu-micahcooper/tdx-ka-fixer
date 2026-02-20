# backend/tests/test_scanner.py
from datetime import datetime, timedelta
from services.scanner import HeuristicScanner

def make_article(**kwargs):
    defaults = {
        "tdx_id": 1, "title": "Test", "body": "Normal content here with enough words to be valid.",
        "category_id": 1, "category_name": "Cat",
        "created_at": datetime.utcnow() - timedelta(days=30),
        "modified_at": datetime.utcnow() - timedelta(days=5),
        "view_count": 10, "status": "active",
    }
    defaults.update(kwargs)
    return defaults

def test_old_unmodified_article_scores_low():
    scanner = HeuristicScanner(threshold=5.0)
    article = make_article(modified_at=datetime.utcnow() - timedelta(days=400))
    score = scanner.score(article)
    assert score < 5.0

def test_todo_in_body_scores_low():
    scanner = HeuristicScanner(threshold=5.0)
    article = make_article(body="TODO: finish this article")
    score = scanner.score(article)
    assert score < 5.0

def test_very_short_body_scores_low():
    scanner = HeuristicScanner(threshold=5.0)
    article = make_article(body="Short.")
    score = scanner.score(article)
    assert score < 5.0

def test_healthy_article_scores_above_threshold():
    scanner = HeuristicScanner(threshold=5.0)
    article = make_article(
        body="A" * 300,
        modified_at=datetime.utcnow() - timedelta(days=10),
        view_count=50,
    )
    score = scanner.score(article)
    assert score >= 5.0

def test_needs_review_returns_true_below_threshold():
    scanner = HeuristicScanner(threshold=5.0)
    article = make_article(body="TODO: stub")
    assert scanner.needs_review(article) is True

def test_needs_review_returns_false_above_threshold():
    scanner = HeuristicScanner(threshold=5.0)
    article = make_article(
        body="A" * 300,
        modified_at=datetime.utcnow() - timedelta(days=10),
    )
    assert scanner.needs_review(article) is False
