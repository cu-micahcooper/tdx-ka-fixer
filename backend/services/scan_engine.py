# backend/services/scan_engine.py
import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from models import Article, AnalysisResult, ReviewQueue, ScanJob, AppSettings
from services.scanner import HeuristicScanner
from services.tdx_client import TDXClient
from services.claude_client import ClaudeAnalyzer


def _parse_date(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


class ScanEngine:
    def __init__(self, db: Session, tdx_client: TDXClient,
                 analyzer: ClaudeAnalyzer, heuristic_threshold: float = 5.0):
        self.db = db
        self.tdx = tdx_client
        self.analyzer = analyzer
        self.heuristic = HeuristicScanner(threshold=heuristic_threshold)

    def _sync_article(self, raw: dict) -> Article:
        article = self.db.query(Article).filter_by(tdx_id=raw["ID"]).first()
        tdx_status = raw.get("Status")
        raw_tags = raw.get("Tags") or []
        tags_str = ", ".join(str(t) for t in raw_tags) if raw_tags else ""
        data = dict(
            title=raw.get("Subject", ""),
            body=raw.get("Body", ""),
            category_id=raw.get("CategoryID"),
            category_name=raw.get("CategoryName"),
            created_at=_parse_date(raw.get("CreatedDate")),
            modified_at=_parse_date(raw.get("ModifiedDate")),
            view_count=raw.get("NumViews", 0),
            last_synced_at=datetime.now(timezone.utc).replace(tzinfo=None),
            tdx_status=tdx_status,
            is_public=bool(raw.get("IsPublic", False)),
            status="archived" if tdx_status == 5 else "active",
            tags=tags_str,
        )
        if article:
            for k, v in data.items():
                setattr(article, k, v)
        else:
            article = Article(tdx_id=raw["ID"], **data)
            self.db.add(article)
        self.db.flush()
        return article

    def _load_directive(self, is_public: bool) -> str:
        row = self.db.query(AppSettings).first()
        if row is None:
            return ""
        return row.public_directive if is_public else row.internal_directive

    def _analyze_and_queue(self, article: Article, directive: str = "") -> bool:
        # Skip if already pending in queue; return False to indicate no new entry
        existing = (
            self.db.query(ReviewQueue)
            .filter_by(article_id=article.id, status="pending")
            .first()
        )
        if existing:
            return False
        result = self.analyzer.analyze(title=article.title, body=article.body, directive=directive, tags=article.tags or "")
        analysis = AnalysisResult(
            article_id=article.id,
            model_used=getattr(self.analyzer, "model", "unknown"),
            score_clarity=result.score_clarity,
            score_completeness=result.score_completeness,
            score_findability=result.score_findability,
            score_redundancy=result.score_redundancy,
            score_accuracy=result.score_accuracy,
            overall_score=result.overall_score,
            issue_summary=result.issue_summary,
            defects_json=json.dumps(result.defects),
            proposed_body=result.proposed_body,
            approval_tier=result.approval_tier,
        )
        self.db.add(analysis)
        self.db.flush()
        queue_item = ReviewQueue(article_id=article.id, analysis_id=analysis.id)
        self.db.add(queue_item)
        return True

    def run_heuristic_scan(self) -> ScanJob:
        job = ScanJob(mode="heuristic")
        self.db.add(job)
        self.db.commit()  # commit immediately so job is visible during scan
        try:
            raw_articles = self.tdx.list_articles()
            job.articles_total = len(raw_articles)
            self.db.commit()
            flagged = 0
            for i, raw in enumerate(raw_articles):
                article = self._sync_article(raw)
                article_dict = {
                    "body": article.body,
                    "modified_at": article.modified_at,
                    "created_at": article.created_at,
                    "view_count": article.view_count,
                }
                score = self.heuristic.score(article_dict)
                article.heuristic_score = score
                job.articles_scanned = i + 1
                self.db.commit()  # release write lock between articles
                if self.heuristic.needs_review(article_dict):
                    directive = self._load_directive(bool(article.is_public))
                    if self._analyze_and_queue(article, directive=directive):
                        flagged += 1
                        self.db.commit()
            job.articles_flagged = flagged
            job.status = "complete"
            job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            self.db.commit()
        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            self.db.commit()
            raise
        return job

    def run_full_batch_scan(self) -> ScanJob:
        job = ScanJob(mode="full_batch")
        self.db.add(job)
        self.db.commit()  # commit immediately so job is visible during scan
        try:
            raw_articles = self.tdx.list_articles()
            job.articles_total = len(raw_articles)
            self.db.commit()
            flagged = 0
            for i, raw in enumerate(raw_articles):
                article = self._sync_article(raw)
                job.articles_scanned = i + 1
                self.db.commit()  # release write lock between articles
                directive = self._load_directive(bool(article.is_public))
                if self._analyze_and_queue(article, directive=directive):
                    flagged += 1
                    self.db.commit()
            job.articles_flagged = flagged
            job.status = "complete"
            job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            self.db.commit()
        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            self.db.commit()
            raise
        return job
