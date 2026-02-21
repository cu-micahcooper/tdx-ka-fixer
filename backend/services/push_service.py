# backend/services/push_service.py
import re
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from models import ApprovedChange, Article, AuditLog


def _normalize_anchors(html: str) -> str:
    """
    TDX sanitizes HTML and strips `id` attributes from block elements, which
    breaks in-page anchor links like <a href="#section">.

    Convert <hN id="foo"> to <a name="foo"></a><hN> so the anchor target
    survives TDX's sanitizer. The `name` attribute on <a> tags is preserved.
    """
    def _replace(m: re.Match) -> str:
        tag = m.group(1)           # e.g. "h2"
        anchor_id = m.group(2)     # e.g. "stack3plus"
        rest = re.sub(r'\s+id="[^"]*"', '', m.group(3))  # attrs minus id
        return f'<a name="{anchor_id}"></a><{tag}{rest}>'

    return re.sub(
        r'<(h[1-6])\s[^>]*\bid="([^"]+)"([^>]*)>',
        _replace,
        html,
    )


class PushService:
    def __init__(self, db: Session, tdx_client):
        self.db = db
        self.tdx = tdx_client

    def push(self, approved_change_id: int) -> AuditLog:
        change = self.db.get(ApprovedChange, approved_change_id)
        if not change:
            raise ValueError(f"ApprovedChange {approved_change_id} not found")
        article = self.db.get(Article, change.article_id)
        tdx_body = _normalize_anchors(change.approved_body)
        try:
            self.tdx.update_article(article.tdx_id, tdx_body)
            change.push_status = "success"
            change.push_error = None
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
        """Push all approved changes that haven't been successfully pushed yet (pending or failed)."""
        unpushed = (
            self.db.query(ApprovedChange)
            .filter(ApprovedChange.push_status.in_(["pending", "failed"]))
            .all()
        )
        results = []
        for c in unpushed:
            try:
                results.append(self.push(c.id))
            except Exception:
                pass  # push() already marks change as failed and commits
        return results
