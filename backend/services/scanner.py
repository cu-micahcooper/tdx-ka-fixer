# backend/services/scanner.py
import re
from datetime import datetime, timezone

DEFECT_PATTERNS = [
    r"\bTODO\b", r"\bTBD\b", r"\bPLACEHOLDER\b",
    r"\bFIXME\b", r"\bXXX\b", r"\[INSERT\b",
]

# Minimum character length considered "substantial" even if word count is low
_MIN_CHARS_SUBSTANTIAL = 100

class HeuristicScanner:
    def __init__(self, threshold: float = 5.0):
        self.threshold = threshold

    def score(self, article: dict) -> float:
        """Return a 0-10 quality score using cheap heuristics only."""
        score = 10.0

        # Age penalty: >365 days without modification
        modified_at = article.get("modified_at")
        if modified_at:
            if modified_at.tzinfo is not None:
                now = datetime.now(timezone.utc)
            else:
                now = datetime.utcnow()
            age_days = (now - modified_at).days
            if age_days > 365:
                score -= 3.0
            elif age_days > 180:
                score -= 1.5

        # Length penalty: strip HTML tags, count words and characters
        body = article.get("body", "")
        body_text = re.sub(r"<[^>]+>", "", body)
        word_count = len(body_text.split())
        char_count = len(body_text.strip())
        # Only apply word-count penalties when the body is not substantial by character length
        if char_count < _MIN_CHARS_SUBSTANTIAL:
            if word_count < 20:
                score -= 6.0
            elif word_count < 50:
                score -= 2.0

        # Defect pattern penalty
        for pattern in DEFECT_PATTERNS:
            if re.search(pattern, body, re.IGNORECASE):
                score -= 2.0
                break

        # Low engagement penalty
        view_count = article.get("view_count", 0)
        created_at = article.get("created_at")
        if created_at and view_count is not None:
            if created_at.tzinfo is not None:
                now = datetime.now(timezone.utc)
            else:
                now = datetime.utcnow()
            age_days = max((now - created_at).days, 1)
            views_per_month = (view_count / age_days) * 30
            if views_per_month < 1 and age_days > 90:
                score -= 1.5

        return max(0.0, round(score, 2))

    def needs_review(self, article: dict) -> bool:
        return self.score(article) < self.threshold
