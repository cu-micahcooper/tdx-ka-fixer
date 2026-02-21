# backend/routers/stats.py
from fastapi import APIRouter, Depends
from sqlalchemy import func, case
from sqlalchemy.orm import Session
from database import get_db
from models import Article

router = APIRouter(prefix="/api/stats", tags=["stats"])

_TDX_STATUS_LABEL: dict[int, str] = {
    1: "Draft",
    2: "Submitted",
    3: "Published",
    5: "Archived",
}


@router.get("")
def get_stats(db: Session = Depends(get_db)):
    needs_review_expr = case((Article.heuristic_score < 5, 1), else_=0)

    # Overall
    total = db.query(func.count(Article.id)).scalar() or 0
    avg_score = db.query(func.avg(Article.heuristic_score)).scalar()
    needs_review = db.query(func.sum(needs_review_expr)).scalar() or 0

    # By publish status (tdx_status)
    by_status_rows = (
        db.query(
            Article.tdx_status,
            func.count(Article.id).label("count"),
            func.avg(Article.heuristic_score).label("avg_score"),
            func.sum(needs_review_expr).label("needs_review"),
        )
        .group_by(Article.tdx_status)
        .order_by(func.count(Article.id).desc())
        .all()
    )
    by_publish_status = [
        {
            "tdx_status": r.tdx_status,
            "label": _TDX_STATUS_LABEL.get(r.tdx_status, "Unknown") if r.tdx_status else "Unknown",
            "count": r.count,
            "avg_score": round(r.avg_score, 2) if r.avg_score is not None else None,
            "needs_review": r.needs_review or 0,
        }
        for r in by_status_rows
    ]

    # By visibility (is_public)
    by_vis_rows = (
        db.query(
            Article.is_public,
            func.count(Article.id).label("count"),
            func.avg(Article.heuristic_score).label("avg_score"),
            func.sum(needs_review_expr).label("needs_review"),
        )
        .group_by(Article.is_public)
        .all()
    )
    by_visibility = [
        {
            "is_public": bool(r.is_public),
            "label": "Public" if r.is_public else "Internal",
            "count": r.count,
            "avg_score": round(r.avg_score, 2) if r.avg_score is not None else None,
            "needs_review": r.needs_review or 0,
        }
        for r in by_vis_rows
    ]
    # Ensure Public first
    by_visibility.sort(key=lambda x: (0 if x["is_public"] else 1))

    # By category (all, sorted by count desc)
    by_cat_rows = (
        db.query(
            Article.category_name,
            func.count(Article.id).label("count"),
            func.avg(Article.heuristic_score).label("avg_score"),
            func.sum(needs_review_expr).label("needs_review"),
        )
        .group_by(Article.category_name)
        .order_by(func.count(Article.id).desc())
        .all()
    )
    by_category = [
        {
            "category_name": r.category_name or "Uncategorized",
            "count": r.count,
            "avg_score": round(r.avg_score, 2) if r.avg_score is not None else None,
            "needs_review": r.needs_review or 0,
        }
        for r in by_cat_rows
    ]

    return {
        "total_articles": total,
        "avg_heuristic_score": round(avg_score, 2) if avg_score is not None else None,
        "needs_review_count": int(needs_review),
        "by_publish_status": by_publish_status,
        "by_visibility": by_visibility,
        "by_category": by_category,
    }
