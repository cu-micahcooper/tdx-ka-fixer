# backend/models.py
from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, ForeignKey, func
)
from sqlalchemy.orm import DeclarativeBase, relationship

class Base(DeclarativeBase):
    pass

class Article(Base):
    __tablename__ = "articles"
    id = Column(Integer, primary_key=True)
    tdx_id = Column(Integer, unique=True, nullable=False)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    category_id = Column(Integer)
    category_name = Column(String)
    created_at = Column(DateTime)
    modified_at = Column(DateTime)
    last_synced_at = Column(DateTime, server_default=func.now())
    view_count = Column(Integer, default=0)
    heuristic_score = Column(Float, default=10.0)
    status = Column(String, default="active")
    analyses = relationship("AnalysisResult", back_populates="article")
    queue_items = relationship("ReviewQueue", back_populates="article")

class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    analyzed_at = Column(DateTime, server_default=func.now())
    model_used = Column(String)
    score_clarity = Column(Float)
    score_completeness = Column(Float)
    score_findability = Column(Float)
    score_redundancy = Column(Float)
    score_accuracy = Column(Float)
    overall_score = Column(Float)
    issue_summary = Column(Text)
    defects_json = Column(Text)
    proposed_body = Column(Text)
    approval_tier = Column(String)
    article = relationship("Article", back_populates="analyses")
    queue_items = relationship("ReviewQueue", back_populates="analysis")

class ReviewQueue(Base):
    __tablename__ = "review_queue"
    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    analysis_id = Column(Integer, ForeignKey("analysis_results.id"), nullable=False)
    queued_at = Column(DateTime, server_default=func.now())
    status = Column(String, default="pending")
    reviewer_note = Column(Text)
    reviewed_at = Column(DateTime)
    article = relationship("Article", back_populates="queue_items")
    analysis = relationship("AnalysisResult", back_populates="queue_items")
    approved_change = relationship("ApprovedChange", back_populates="queue_item", uselist=False)

class ApprovedChange(Base):
    __tablename__ = "approved_changes"
    id = Column(Integer, primary_key=True)
    review_queue_id = Column(Integer, ForeignKey("review_queue.id"), nullable=False)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    original_body = Column(Text)
    approved_body = Column(Text)
    approved_at = Column(DateTime, server_default=func.now())
    pushed_at = Column(DateTime)
    push_status = Column(String, default="pending")
    push_error = Column(Text)
    queue_item = relationship("ReviewQueue", back_populates="approved_change")

class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    tdx_id = Column(Integer, nullable=False)
    action = Column(String, nullable=False)
    original_body = Column(Text)
    new_body = Column(Text)
    approved_at = Column(DateTime)
    pushed_at = Column(DateTime, server_default=func.now())
    reverted_at = Column(DateTime)

class ScanJob(Base):
    __tablename__ = "scan_jobs"
    id = Column(Integer, primary_key=True)
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime)
    mode = Column(String, nullable=False)
    articles_scanned = Column(Integer, default=0)
    articles_flagged = Column(Integer, default=0)
    status = Column(String, default="running")
    error = Column(Text)
