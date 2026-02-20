# backend/services/push_service.py
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from models import ApprovedChange, Article, AuditLog


class PushService:
    def __init__(self, db: Session, tdx_client):
        self.db = db
        self.tdx = tdx_client

    def push(self, approved_change_id: int) -> AuditLog:
        change = self.db.get(ApprovedChange, approved_change_id)
        if not change:
            raise ValueError(f"ApprovedChange {approved_change_id} not found")
        article = self.db.get(Article, change.article_id)
        try:
            self.tdx.update_article(article.tdx_id, change.approved_body)
            change.push_status = "success"
            change.pushed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            article.body = change.approved_body
            log = AuditLog(
                article_id=article.id,
                tdx_id=article.tdx_id,
                action="update",
                original_body=change.original_body,
                new_body=change.approved_body,
                approved_at=change.approved_at,
            )
            self.db.add(log)
            self.db.commit()
            return log
        except Exception as e:
            change.push_status = "failed"
            change.push_error = str(e)
            self.db.commit()
            raise

    def push_all_pending(self) -> list[AuditLog]:
        pending = (
            self.db.query(ApprovedChange)
            .filter_by(push_status="pending")
            .all()
        )
        return [self.push(c.id) for c in pending]
