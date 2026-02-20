# backend/services/approval.py
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from models import ReviewQueue, ApprovedChange, Article, AnalysisResult


class ApprovalService:
    def __init__(self, db: Session):
        self.db = db

    def approve(self, queue_item_id: int, edited_body: str | None = None) -> ApprovedChange:
        qi = self.db.get(ReviewQueue, queue_item_id)
        if not qi:
            raise ValueError(f"Queue item {queue_item_id} not found")
        analysis = self.db.get(AnalysisResult, qi.analysis_id)
        article = self.db.get(Article, qi.article_id)
        approved_body = edited_body if edited_body is not None else analysis.proposed_body
        change = ApprovedChange(
            review_queue_id=qi.id,
            article_id=article.id,
            original_body=article.body,
            approved_body=approved_body,
        )
        self.db.add(change)
        qi.status = "approved"
        qi.reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        self.db.commit()
        return change

    def reject(self, queue_item_id: int, note: str = "") -> ReviewQueue:
        qi = self.db.get(ReviewQueue, queue_item_id)
        if not qi:
            raise ValueError(f"Queue item {queue_item_id} not found")
        qi.status = "rejected"
        qi.reviewer_note = note
        qi.reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        self.db.commit()
        return qi

    def skip(self, queue_item_id: int) -> ReviewQueue:
        qi = self.db.get(ReviewQueue, queue_item_id)
        if not qi:
            raise ValueError(f"Queue item {queue_item_id} not found")
        qi.status = "skipped"
        qi.reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        self.db.commit()
        return qi
