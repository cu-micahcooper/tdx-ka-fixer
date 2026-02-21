# backend/routers/articles.py
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Article, AnalysisResult, ReviewQueue
from config import get_settings

router = APIRouter(prefix="/api/articles", tags=["articles"])


def _article_url(tdx_id: int) -> str:
    s = get_settings()
    portal_base = s.tdx_base_url.replace("/TDWebApi", "").rstrip("/")
    return f"{portal_base}/TDClient/{s.tdx_app_id}/Portal/KB/ArticleDet?ID={tdx_id}"


_TDX_STATUS_LABEL: dict[int, str] = {
    1: "draft",
    2: "submitted",
    3: "published",
    5: "archived",
}


def _article_row(a: Article) -> dict:
    return {
        "id": a.id,
        "tdx_id": a.tdx_id,
        "title": a.title,
        "body": a.body,
        "category_id": a.category_id,
        "category_name": a.category_name,
        "modified_at": a.modified_at.isoformat() + "Z" if a.modified_at else None,
        "heuristic_score": a.heuristic_score,
        "status": a.status,
        "tdx_status": a.tdx_status,
        "tdx_status_label": _TDX_STATUS_LABEL.get(a.tdx_status, "unknown") if a.tdx_status else None,
        "is_public": bool(a.is_public),
        "view_count": getattr(a, "view_count", 0),
        "tdx_url": _article_url(a.tdx_id),
    }


@router.get("")
def list_articles(
    status: str | None = None,
    tdx_status: int | None = None,
    is_public: bool | None = None,
    category_id: int | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(Article)
    if status:
        q = q.filter(Article.status == status)
    if tdx_status is not None:
        q = q.filter(Article.tdx_status == tdx_status)
    if is_public is not None:
        q = q.filter(Article.is_public == is_public)
    if category_id:
        q = q.filter(Article.category_id == category_id)
    return [_article_row(a) for a in q.order_by(Article.heuristic_score).all()]


@router.get("/{article_id}")
def get_article(article_id: int, db: Session = Depends(get_db)):
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return _article_row(article)


@router.get("/{article_id}/analysis")
def get_article_analysis(article_id: int, db: Session = Depends(get_db)):
    """Return the latest analysis and current queue status for an article."""
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    analysis = (
        db.query(AnalysisResult)
        .filter_by(article_id=article_id)
        .order_by(AnalysisResult.analyzed_at.desc())
        .first()
    )

    queue_item = None
    if analysis:
        queue_item = (
            db.query(ReviewQueue)
            .filter_by(analysis_id=analysis.id)
            .order_by(ReviewQueue.queued_at.desc())
            .first()
        )

    return {
        "article": {
            "id": article.id,
            "tdx_id": article.tdx_id,
            "title": article.title,
            "body": article.body,
            "category_name": article.category_name,
            "heuristic_score": article.heuristic_score,
            "status": article.status,
            "tdx_status": article.tdx_status,
            "tdx_status_label": _TDX_STATUS_LABEL.get(article.tdx_status, "unknown") if article.tdx_status else None,
            "is_public": bool(article.is_public),
            "view_count": article.view_count,
            "modified_at": article.modified_at.isoformat() + "Z" if article.modified_at else None,
            "last_synced_at": article.last_synced_at.isoformat() + "Z" if article.last_synced_at else None,
            "tdx_url": _article_url(article.tdx_id),
        },
        "analysis": {
            "id": analysis.id,
            "overall_score": analysis.overall_score,
            "score_clarity": analysis.score_clarity,
            "score_completeness": analysis.score_completeness,
            "score_findability": analysis.score_findability,
            "score_redundancy": analysis.score_redundancy,
            "score_accuracy": analysis.score_accuracy,
            "issue_summary": analysis.issue_summary,
            "defects": json.loads(analysis.defects_json) if analysis.defects_json else [],
            "proposed_body": analysis.proposed_body,
            "approval_tier": analysis.approval_tier,
            "analyzed_at": analysis.analyzed_at.isoformat() + "Z" if analysis.analyzed_at else None,
        } if analysis else None,
        "queue_item": {
            "id": queue_item.id,
            "status": queue_item.status,
            "reviewer_note": queue_item.reviewer_note,
        } if queue_item else None,
    }
