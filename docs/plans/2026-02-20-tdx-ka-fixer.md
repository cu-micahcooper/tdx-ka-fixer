# TDX KA Fixer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a locally-run web application that fetches TeamDynamix KB articles, analyzes and rewrites them using Claude AI, and provides a browser-based approval workflow before pushing changes back to TDX.

**Architecture:** Python FastAPI backend with APScheduler for background scanning, React+TypeScript frontend for the web console, SQLite for local state. Articles are pre-filtered by cheap heuristics, then analyzed by Claude across five KCS quality dimensions. Changes are tiered by severity and require human approval before writing back to TDX.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, APScheduler, Anthropic SDK, httpx, React 18, TypeScript, Vite, SQLite

---

## Phase 1: Backend Foundation

### Task 1: Project scaffold and dependencies

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/requirements-dev.txt`
- Create: `.env.example`
- Create: `.gitignore` (append entries)

**Step 1: Create backend/requirements.txt**

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
sqlalchemy==2.0.36
httpx==0.27.0
anthropic==0.40.0
apscheduler==3.10.4
python-dotenv==1.0.1
pydantic-settings==2.6.0
alembic==1.14.0
```

**Step 2: Create backend/requirements-dev.txt**

```
pytest==8.3.3
pytest-asyncio==0.24.0
pytest-cov==6.0.0
respx==0.21.1
httpx==0.27.0
```

**Step 3: Create .env.example**

```
ANTHROPIC_API_KEY=
TDX_BASE_URL=https://your-instance.teamdynamix.com/TDWebApi
TDX_APP_ID=
TDX_BEID=
TDX_WEB_SERVICES_KEY=
SCAN_CRON=0 2 * * *
HEURISTIC_THRESHOLD=5.0
```

**Step 4: Append to .gitignore**

```
.env
ka_fixer.db
__pycache__/
*.pyc
.pytest_cache/
.venv/
node_modules/
dist/
```

**Step 5: Create virtual environment and install deps**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

**Step 6: Commit**

```bash
git add backend/requirements.txt backend/requirements-dev.txt .env.example .gitignore
git commit -m "feat: add backend dependencies and project scaffold"
```

---

### Task 2: Config and settings

**Files:**
- Create: `backend/config.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/test_config.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_config.py
import os
import pytest
from unittest.mock import patch

def test_settings_loads_from_env():
    env = {
        "ANTHROPIC_API_KEY": "test-key",
        "TDX_BASE_URL": "https://test.tdx.com/TDWebApi",
        "TDX_APP_ID": "42",
        "TDX_BEID": "beid-value",
        "TDX_WEB_SERVICES_KEY": "wskey-value",
    }
    with patch.dict(os.environ, env):
        from config import Settings
        s = Settings()
        assert s.anthropic_api_key == "test-key"
        assert s.tdx_app_id == 42
        assert s.tdx_base_url == "https://test.tdx.com/TDWebApi"

def test_settings_missing_required_raises():
    with patch.dict(os.environ, {}, clear=True):
        from config import Settings
        with pytest.raises(Exception):
            Settings()
```

**Step 2: Run test to confirm it fails**

```bash
cd backend && python -m pytest tests/test_config.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'config'`

**Step 3: Implement config.py**

```python
# backend/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    anthropic_api_key: str
    tdx_base_url: str
    tdx_app_id: int
    tdx_beid: str
    tdx_web_services_key: str
    scan_cron: str = "0 2 * * *"
    heuristic_threshold: float = 5.0
    claude_model: str = "claude-sonnet-4-6"

    class Config:
        env_file = ".env"

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

**Step 4: Run test to confirm it passes**

```bash
python -m pytest tests/test_config.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add backend/config.py backend/tests/
git commit -m "feat: add pydantic settings config"
```

---

### Task 3: Database models and setup

**Files:**
- Create: `backend/database.py`
- Create: `backend/models.py`
- Create: `backend/tests/test_models.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_models.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from models import Base, Article, AnalysisResult, ReviewQueue, ApprovedChange, AuditLog, ScanJob

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_article_create(db):
    article = Article(
        tdx_id=101,
        title="Test Article",
        body="Some content",
        category_id=1,
        category_name="General",
        heuristic_score=7.5,
        status="active",
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    assert article.id is not None
    assert article.title == "Test Article"

def test_analysis_result_links_to_article(db):
    article = Article(tdx_id=102, title="Art", body="Body",
                      category_id=1, category_name="Cat",
                      heuristic_score=4.0, status="active")
    db.add(article)
    db.commit()
    result = AnalysisResult(
        article_id=article.id,
        model_used="claude-sonnet-4-6",
        score_clarity=7.0, score_completeness=6.0,
        score_findability=5.0, score_redundancy=8.0, score_accuracy=7.0,
        overall_score=6.6,
        issue_summary="Needs work",
        defects_json="[]",
        proposed_body="Better body",
        approval_tier="confirm",
    )
    db.add(result)
    db.commit()
    assert result.article_id == article.id
```

**Step 2: Run test to confirm it fails**

```bash
python -m pytest tests/test_models.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'models'`

**Step 3: Implement database.py**

```python
# backend/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

DATABASE_URL = "sqlite:///./ka_fixer.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Step 4: Implement models.py**

```python
# backend/models.py
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, ForeignKey
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
    last_synced_at = Column(DateTime, default=datetime.utcnow)
    view_count = Column(Integer, default=0)
    heuristic_score = Column(Float, default=10.0)
    status = Column(String, default="active")
    analyses = relationship("AnalysisResult", back_populates="article")
    queue_items = relationship("ReviewQueue", back_populates="article")

class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    analyzed_at = Column(DateTime, default=datetime.utcnow)
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
    queued_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="pending")  # pending/approved/rejected/skipped
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
    approved_at = Column(DateTime, default=datetime.utcnow)
    pushed_at = Column(DateTime)
    push_status = Column(String, default="pending")  # pending/success/failed
    push_error = Column(Text)
    queue_item = relationship("ReviewQueue", back_populates="approved_change")

class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    tdx_id = Column(Integer, nullable=False)
    action = Column(String, nullable=False)  # update/archive
    original_body = Column(Text)
    new_body = Column(Text)
    approved_at = Column(DateTime)
    pushed_at = Column(DateTime, default=datetime.utcnow)
    reverted_at = Column(DateTime)

class ScanJob(Base):
    __tablename__ = "scan_jobs"
    id = Column(Integer, primary_key=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    mode = Column(String, nullable=False)  # heuristic/full_batch
    articles_scanned = Column(Integer, default=0)
    articles_flagged = Column(Integer, default=0)
    status = Column(String, default="running")  # running/complete/failed
    error = Column(Text)
```

**Step 5: Run test to confirm it passes**

```bash
python -m pytest tests/test_models.py -v
```
Expected: PASS

**Step 6: Commit**

```bash
git add backend/database.py backend/models.py
git commit -m "feat: add SQLAlchemy models and database setup"
```

---

### Task 4: FastAPI app entry point

**Files:**
- Create: `backend/main.py`
- Create: `backend/tests/test_main.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_main.py
import pytest
from fastapi.testclient import TestClient

def test_health_check():
    from main import app
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

**Step 2: Run test to confirm it fails**

```bash
python -m pytest tests/test_main.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'main'`

**Step 3: Implement main.py**

```python
# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine
from models import Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="TDX KA Fixer", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}
```

**Step 4: Run test to confirm it passes**

```bash
python -m pytest tests/test_main.py -v
```
Expected: PASS

**Step 5: Confirm server starts**

```bash
uvicorn main:app --reload --port 8000
```
Expected: Server running at http://127.0.0.1:8000. Visit http://127.0.0.1:8000/docs to see OpenAPI docs.

**Step 6: Commit**

```bash
git add backend/main.py
git commit -m "feat: add FastAPI app entry point with health check"
```

---

## Phase 2: TDX Integration

### Task 5: TDX API client — authentication

**Files:**
- Create: `backend/services/tdx_client.py`
- Create: `backend/services/__init__.py`
- Create: `backend/tests/test_tdx_client.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_tdx_client.py
import pytest
import respx
import httpx
from unittest.mock import patch
from services.tdx_client import TDXClient

TDX_BASE = "https://test.tdx.com/TDWebApi"

@pytest.fixture
def client():
    return TDXClient(
        base_url=TDX_BASE,
        app_id=42,
        beid="test-beid",
        web_services_key="test-wskey",
    )

@respx.mock
def test_authenticate_stores_token(client):
    respx.post(f"{TDX_BASE}/api/auth/loginadmin").mock(
        return_value=httpx.Response(200, json="fake-token-string")
    )
    client.authenticate()
    assert client.token == "fake-token-string"

@respx.mock
def test_authenticate_raises_on_failure(client):
    respx.post(f"{TDX_BASE}/api/auth/loginadmin").mock(
        return_value=httpx.Response(401, text="Unauthorized")
    )
    with pytest.raises(RuntimeError, match="TDX auth failed"):
        client.authenticate()
```

**Step 2: Run test to confirm it fails**

```bash
python -m pytest tests/test_tdx_client.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'services'`

**Step 3: Implement TDXClient authentication**

```python
# backend/services/__init__.py
# (empty)

# backend/services/tdx_client.py
import httpx
from typing import Optional

class TDXClient:
    def __init__(self, base_url: str, app_id: int, beid: str, web_services_key: str):
        self.base_url = base_url.rstrip("/")
        self.app_id = app_id
        self.beid = beid
        self.web_services_key = web_services_key
        self.token: Optional[str] = None

    def authenticate(self) -> None:
        url = f"{self.base_url}/api/auth/loginadmin"
        payload = {"BEID": self.beid, "WebServicesKey": self.web_services_key}
        with httpx.Client() as http:
            response = http.post(url, json=payload)
        if response.status_code != 200:
            raise RuntimeError(f"TDX auth failed: {response.status_code} {response.text}")
        self.token = response.json()

    def _headers(self) -> dict:
        if not self.token:
            self.authenticate()
        return {"Authorization": f"Bearer {self.token}"}
```

**Step 4: Run test to confirm it passes**

```bash
python -m pytest tests/test_tdx_client.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add backend/services/
git commit -m "feat: add TDX API client with authentication"
```

---

### Task 6: TDX client — fetch and sync articles

**Files:**
- Modify: `backend/services/tdx_client.py`
- Modify: `backend/tests/test_tdx_client.py`

**Step 1: Add failing tests**

Add to `backend/tests/test_tdx_client.py`:

```python
SAMPLE_ARTICLE = {
    "ID": 123,
    "Subject": "How to reset password",
    "Body": "<p>Click forgot password.</p>",
    "CategoryID": 5,
    "CategoryName": "Account",
    "CreatedDate": "2024-01-01T00:00:00Z",
    "ModifiedDate": "2024-06-01T00:00:00Z",
    "NumViews": 42,
    "IsActive": True,
}

@respx.mock
def test_list_articles(client):
    client.token = "fake-token"
    respx.post(f"{TDX_BASE}/api/42/knowledgebase/search").mock(
        return_value=httpx.Response(200, json=[SAMPLE_ARTICLE])
    )
    articles = client.list_articles()
    assert len(articles) == 1
    assert articles[0]["ID"] == 123

@respx.mock
def test_get_article(client):
    client.token = "fake-token"
    respx.get(f"{TDX_BASE}/api/42/knowledgebase/123").mock(
        return_value=httpx.Response(200, json=SAMPLE_ARTICLE)
    )
    article = client.get_article(123)
    assert article["Subject"] == "How to reset password"

@respx.mock
def test_update_article(client):
    client.token = "fake-token"
    respx.post(f"{TDX_BASE}/api/42/knowledgebase/123").mock(
        return_value=httpx.Response(200, json={**SAMPLE_ARTICLE, "Body": "New body"})
    )
    result = client.update_article(123, "New body")
    assert result["Body"] == "New body"
```

**Step 2: Run test to confirm it fails**

```bash
python -m pytest tests/test_tdx_client.py::test_list_articles -v
```
Expected: FAIL — `AttributeError: 'TDXClient' object has no attribute 'list_articles'`

**Step 3: Add methods to TDXClient**

Append to `backend/services/tdx_client.py`:

```python
    def list_articles(self, max_results: int = 5000) -> list[dict]:
        url = f"{self.base_url}/api/{self.app_id}/knowledgebase/search"
        payload = {"MaxResults": max_results, "IsActive": True}
        with httpx.Client() as http:
            response = http.post(url, json=payload, headers=self._headers())
        response.raise_for_status()
        return response.json()

    def get_article(self, article_id: int) -> dict:
        url = f"{self.base_url}/api/{self.app_id}/knowledgebase/{article_id}"
        with httpx.Client() as http:
            response = http.get(url, headers=self._headers())
        response.raise_for_status()
        return response.json()

    def update_article(self, article_id: int, new_body: str) -> dict:
        url = f"{self.base_url}/api/{self.app_id}/knowledgebase/{article_id}"
        with httpx.Client() as http:
            response = http.post(url, json={"Body": new_body}, headers=self._headers())
        response.raise_for_status()
        return response.json()

    def list_categories(self) -> list[dict]:
        url = f"{self.base_url}/api/{self.app_id}/knowledgebase/categories"
        with httpx.Client() as http:
            response = http.get(url, headers=self._headers())
        response.raise_for_status()
        return response.json()
```

**Step 4: Run all TDX client tests**

```bash
python -m pytest tests/test_tdx_client.py -v
```
Expected: All PASS

**Step 5: Commit**

```bash
git add backend/services/tdx_client.py backend/tests/test_tdx_client.py
git commit -m "feat: add TDX article list/get/update methods"
```

---

## Phase 3: Analysis Pipeline

### Task 7: Heuristic scanner

**Files:**
- Create: `backend/services/scanner.py`
- Create: `backend/tests/test_scanner.py`

**Step 1: Write failing tests**

```python
# backend/tests/test_scanner.py
from datetime import datetime, timedelta
from services.scanner import HeuristicScanner

def make_article(**kwargs):
    defaults = {
        "tdx_id": 1, "title": "Test", "body": "Normal content here.",
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
```

**Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_scanner.py -v
```
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement HeuristicScanner**

```python
# backend/services/scanner.py
import re
from datetime import datetime, timedelta

DEFECT_PATTERNS = [
    r"\bTODO\b", r"\bTBD\b", r"\bPLACEHOLDER\b",
    r"\bFIXME\b", r"\bXXX\b", r"\[INSERT\b",
]

class HeuristicScanner:
    def __init__(self, threshold: float = 5.0):
        self.threshold = threshold

    def score(self, article: dict) -> float:
        """Return a 0-10 quality score using cheap heuristics only."""
        score = 10.0

        # Age penalty: >365 days without modification
        modified_at = article.get("modified_at")
        if modified_at:
            age_days = (datetime.utcnow() - modified_at).days
            if age_days > 365:
                score -= 3.0
            elif age_days > 180:
                score -= 1.5

        # Length penalty
        body = article.get("body", "")
        body_text = re.sub(r"<[^>]+>", "", body)  # strip HTML
        word_count = len(body_text.split())
        if word_count < 20:
            score -= 4.0
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
            age_days = max((datetime.utcnow() - created_at).days, 1)
            views_per_month = (view_count / age_days) * 30
            if views_per_month < 1 and age_days > 90:
                score -= 1.5

        return max(0.0, round(score, 2))

    def needs_review(self, article: dict) -> bool:
        return self.score(article) < self.threshold
```

**Step 4: Run tests to confirm they pass**

```bash
python -m pytest tests/test_scanner.py -v
```
Expected: All PASS

**Step 5: Commit**

```bash
git add backend/services/scanner.py backend/tests/test_scanner.py
git commit -m "feat: add heuristic scanner with quality scoring"
```

---

### Task 8: Claude analysis client

**Files:**
- Create: `backend/services/claude_client.py`
- Create: `backend/tests/test_claude_client.py`

**Step 1: Write failing tests**

```python
# backend/tests/test_claude_client.py
import pytest
from unittest.mock import MagicMock, patch
from services.claude_client import ClaudeAnalyzer, AnalysisResult

SAMPLE_RESPONSE = """{
  "score_clarity": 6.0,
  "score_completeness": 5.0,
  "score_findability": 7.0,
  "score_redundancy": 8.0,
  "score_accuracy": 6.0,
  "overall_score": 6.4,
  "issue_summary": "Article is incomplete and lacks clear steps.",
  "defects": ["Missing resolution steps", "Vague title"],
  "proposed_body": "<p>Improved content here.</p>",
  "approval_tier": "confirm"
}"""

def test_analyze_returns_analysis_result():
    analyzer = ClaudeAnalyzer(api_key="fake", model="claude-sonnet-4-6")
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=SAMPLE_RESPONSE)]
    with patch.object(analyzer.client.messages, "create", return_value=mock_response):
        result = analyzer.analyze(title="Test Article", body="Some content")
    assert isinstance(result, AnalysisResult)
    assert result.score_clarity == 6.0
    assert result.approval_tier == "confirm"
    assert "Missing resolution steps" in result.defects

def test_analyze_assigns_auto_tier_for_high_score():
    analyzer = ClaudeAnalyzer(api_key="fake", model="claude-sonnet-4-6")
    high_score_response = SAMPLE_RESPONSE.replace('"confirm"', '"auto"')
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=high_score_response)]
    with patch.object(analyzer.client.messages, "create", return_value=mock_response):
        result = analyzer.analyze(title="Good Article", body="Complete content")
    assert result.approval_tier == "auto"
```

**Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_claude_client.py -v
```
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement ClaudeAnalyzer**

```python
# backend/services/claude_client.py
import json
from dataclasses import dataclass
from typing import Optional
import anthropic

ANALYSIS_PROMPT = """You are a knowledge base quality analyst operating within the KCS (Knowledge-Centered Service) framework.

Analyze the following knowledge base article and return a JSON object with this exact structure:
{{
  "score_clarity": <0-10 float>,
  "score_completeness": <0-10 float>,
  "score_findability": <0-10 float>,
  "score_redundancy": <0-10 float>,
  "score_accuracy": <0-10 float>,
  "overall_score": <0-10 float, weighted average>,
  "issue_summary": "<1-2 sentence summary of main issues>",
  "defects": ["<specific defect 1>", "<specific defect 2>", ...],
  "proposed_body": "<full improved HTML body>",
  "approval_tier": "<one of: auto | confirm | admin>"
}}

Scoring dimensions:
- clarity: readability, structure, plain language
- completeness: fully addresses the topic
- findability: descriptive title and searchable content
- redundancy: 10 = unique, lower = overlaps with common KB content
- accuracy: no detectable staleness or outdated references

Approval tier rules:
- "auto": only formatting/typo/whitespace fixes
- "confirm": grammar, clarity, minor content improvements
- "admin": major rewrite, structural change, or archival candidate

Return ONLY the JSON object, no other text.

Article Title: {title}

Article Body:
{body}"""

@dataclass
class AnalysisResult:
    score_clarity: float
    score_completeness: float
    score_findability: float
    score_redundancy: float
    score_accuracy: float
    overall_score: float
    issue_summary: str
    defects: list[str]
    proposed_body: str
    approval_tier: str

class ClaudeAnalyzer:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def analyze(self, title: str, body: str) -> AnalysisResult:
        prompt = ANALYSIS_PROMPT.format(title=title, body=body)
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text
        data = json.loads(raw)
        return AnalysisResult(
            score_clarity=float(data["score_clarity"]),
            score_completeness=float(data["score_completeness"]),
            score_findability=float(data["score_findability"]),
            score_redundancy=float(data["score_redundancy"]),
            score_accuracy=float(data["score_accuracy"]),
            overall_score=float(data["overall_score"]),
            issue_summary=data["issue_summary"],
            defects=data.get("defects", []),
            proposed_body=data["proposed_body"],
            approval_tier=data["approval_tier"],
        )
```

**Step 4: Run tests to confirm they pass**

```bash
python -m pytest tests/test_claude_client.py -v
```
Expected: All PASS

**Step 5: Commit**

```bash
git add backend/services/claude_client.py backend/tests/test_claude_client.py
git commit -m "feat: add Claude article analysis client"
```

---

### Task 9: Scan engine — orchestration

**Files:**
- Create: `backend/services/scan_engine.py`
- Create: `backend/tests/test_scan_engine.py`

**Step 1: Write failing tests**

```python
# backend/tests/test_scan_engine.py
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from models import Base, Article, ScanJob
from services.scan_engine import ScanEngine

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture
def engine_with_mocks(db):
    tdx = MagicMock()
    tdx.list_articles.return_value = [
        {
            "ID": 1, "Subject": "Article 1", "Body": "TODO: fix this",
            "CategoryID": 1, "CategoryName": "Cat",
            "CreatedDate": "2023-01-01T00:00:00Z",
            "ModifiedDate": "2023-01-01T00:00:00Z",
            "NumViews": 2, "IsActive": True,
        }
    ]
    analyzer = MagicMock()
    return ScanEngine(db=db, tdx_client=tdx, analyzer=analyzer, heuristic_threshold=5.0)

def test_heuristic_scan_flags_article(engine_with_mocks, db):
    scan_engine = engine_with_mocks
    job = scan_engine.run_heuristic_scan()
    assert job.articles_scanned == 1
    assert job.articles_flagged == 1
    assert job.status == "complete"

def test_heuristic_scan_syncs_articles_to_db(engine_with_mocks, db):
    engine_with_mocks.run_heuristic_scan()
    articles = db.query(Article).all()
    assert len(articles) == 1
    assert articles[0].tdx_id == 1
```

**Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_scan_engine.py -v
```
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement ScanEngine**

```python
# backend/services/scan_engine.py
import json
from datetime import datetime
from sqlalchemy.orm import Session
from models import Article, AnalysisResult, ReviewQueue, ScanJob
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
        data = dict(
            title=raw.get("Subject", ""),
            body=raw.get("Body", ""),
            category_id=raw.get("CategoryID"),
            category_name=raw.get("CategoryName"),
            created_at=_parse_date(raw.get("CreatedDate")),
            modified_at=_parse_date(raw.get("ModifiedDate")),
            view_count=raw.get("NumViews", 0),
            last_synced_at=datetime.utcnow(),
            status="active" if raw.get("IsActive", True) else "archived",
        )
        if article:
            for k, v in data.items():
                setattr(article, k, v)
        else:
            article = Article(tdx_id=raw["ID"], **data)
            self.db.add(article)
        self.db.flush()
        return article

    def _analyze_and_queue(self, article: Article) -> None:
        result = self.analyzer.analyze(title=article.title, body=article.body)
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

    def run_heuristic_scan(self) -> ScanJob:
        job = ScanJob(mode="heuristic")
        self.db.add(job)
        self.db.flush()
        raw_articles = self.tdx.list_articles()
        flagged = 0
        for raw in raw_articles:
            article = self._sync_article(raw)
            article_dict = {
                "body": article.body,
                "modified_at": article.modified_at,
                "created_at": article.created_at,
                "view_count": article.view_count,
            }
            score = self.heuristic.score(article_dict)
            article.heuristic_score = score
            if self.heuristic.needs_review(article_dict):
                self._analyze_and_queue(article)
                flagged += 1
        job.articles_scanned = len(raw_articles)
        job.articles_flagged = flagged
        job.status = "complete"
        job.completed_at = datetime.utcnow()
        self.db.commit()
        return job

    def run_full_batch_scan(self) -> ScanJob:
        job = ScanJob(mode="full_batch")
        self.db.add(job)
        self.db.flush()
        raw_articles = self.tdx.list_articles()
        for raw in raw_articles:
            article = self._sync_article(raw)
            self._analyze_and_queue(article)
        job.articles_scanned = len(raw_articles)
        job.articles_flagged = len(raw_articles)
        job.status = "complete"
        job.completed_at = datetime.utcnow()
        self.db.commit()
        return job
```

**Step 4: Run tests to confirm they pass**

```bash
python -m pytest tests/test_scan_engine.py -v
```
Expected: All PASS

**Step 5: Commit**

```bash
git add backend/services/scan_engine.py backend/tests/test_scan_engine.py
git commit -m "feat: add scan engine with heuristic and full-batch modes"
```

---

## Phase 4: Approval and Write-back

### Task 10: Approval service

**Files:**
- Create: `backend/services/approval.py`
- Create: `backend/tests/test_approval.py`

**Step 1: Write failing tests**

```python
# backend/tests/test_approval.py
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from models import Base, Article, AnalysisResult, ReviewQueue, ApprovedChange, AuditLog
from services.approval import ApprovalService

@pytest.fixture
def db():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    with Session(eng) as session:
        yield session

def seed_queue_item(db, tier="confirm"):
    article = Article(tdx_id=99, title="Art", body="Original body",
                      category_id=1, category_name="Cat",
                      heuristic_score=4.0, status="active")
    db.add(article)
    db.flush()
    analysis = AnalysisResult(
        article_id=article.id, model_used="test",
        score_clarity=7.0, score_completeness=7.0, score_findability=7.0,
        score_redundancy=7.0, score_accuracy=7.0, overall_score=7.0,
        issue_summary="Minor issues", defects_json="[]",
        proposed_body="Improved body", approval_tier=tier,
    )
    db.add(analysis)
    db.flush()
    qi = ReviewQueue(article_id=article.id, analysis_id=analysis.id)
    db.add(qi)
    db.commit()
    return qi

def test_approve_creates_approved_change(db):
    qi = seed_queue_item(db)
    svc = ApprovalService(db=db)
    svc.approve(queue_item_id=qi.id)
    db.refresh(qi)
    assert qi.status == "approved"
    change = db.query(ApprovedChange).filter_by(review_queue_id=qi.id).first()
    assert change is not None
    assert change.approved_body == "Improved body"
    assert change.original_body == "Original body"

def test_reject_updates_status(db):
    qi = seed_queue_item(db)
    svc = ApprovalService(db=db)
    svc.reject(queue_item_id=qi.id, note="Not relevant")
    db.refresh(qi)
    assert qi.status == "rejected"
    assert qi.reviewer_note == "Not relevant"

def test_approve_with_edit_uses_edited_body(db):
    qi = seed_queue_item(db)
    svc = ApprovalService(db=db)
    svc.approve(queue_item_id=qi.id, edited_body="Manually edited body")
    change = db.query(ApprovedChange).filter_by(review_queue_id=qi.id).first()
    assert change.approved_body == "Manually edited body"
```

**Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_approval.py -v
```
Expected: FAIL

**Step 3: Implement ApprovalService**

```python
# backend/services/approval.py
from datetime import datetime
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
        qi.reviewed_at = datetime.utcnow()
        self.db.commit()
        return change

    def reject(self, queue_item_id: int, note: str = "") -> ReviewQueue:
        qi = self.db.get(ReviewQueue, queue_item_id)
        if not qi:
            raise ValueError(f"Queue item {queue_item_id} not found")
        qi.status = "rejected"
        qi.reviewer_note = note
        qi.reviewed_at = datetime.utcnow()
        self.db.commit()
        return qi

    def skip(self, queue_item_id: int) -> ReviewQueue:
        qi = self.db.get(ReviewQueue, queue_item_id)
        if not qi:
            raise ValueError(f"Queue item {queue_item_id} not found")
        qi.status = "skipped"
        qi.reviewed_at = datetime.utcnow()
        self.db.commit()
        return qi
```

**Step 4: Run tests to confirm they pass**

```bash
python -m pytest tests/test_approval.py -v
```
Expected: All PASS

**Step 5: Commit**

```bash
git add backend/services/approval.py backend/tests/test_approval.py
git commit -m "feat: add approval service with approve/reject/skip"
```

---

### Task 11: TDX write-back service

**Files:**
- Create: `backend/services/push_service.py`
- Create: `backend/tests/test_push_service.py`

**Step 1: Write failing tests**

```python
# backend/tests/test_push_service.py
import pytest
from datetime import datetime
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from models import Base, Article, AnalysisResult, ReviewQueue, ApprovedChange, AuditLog
from services.push_service import PushService

@pytest.fixture
def db():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    with Session(eng) as session:
        yield session

def seed_approved_change(db):
    article = Article(tdx_id=55, title="Art", body="Old body",
                      category_id=1, category_name="Cat",
                      heuristic_score=4.0, status="active")
    db.add(article)
    db.flush()
    analysis = AnalysisResult(
        article_id=article.id, model_used="test",
        score_clarity=8.0, score_completeness=8.0, score_findability=8.0,
        score_redundancy=8.0, score_accuracy=8.0, overall_score=8.0,
        issue_summary="Good", defects_json="[]",
        proposed_body="New body", approval_tier="confirm",
    )
    db.add(analysis)
    db.flush()
    qi = ReviewQueue(article_id=article.id, analysis_id=analysis.id, status="approved")
    db.add(qi)
    db.flush()
    change = ApprovedChange(
        review_queue_id=qi.id, article_id=article.id,
        original_body="Old body", approved_body="New body",
    )
    db.add(change)
    db.commit()
    return change

def test_push_calls_tdx_update(db):
    change = seed_approved_change(db)
    tdx = MagicMock()
    tdx.update_article.return_value = {"Body": "New body"}
    svc = PushService(db=db, tdx_client=tdx)
    svc.push(change.id)
    tdx.update_article.assert_called_once_with(55, "New body")

def test_push_writes_audit_log(db):
    change = seed_approved_change(db)
    tdx = MagicMock()
    tdx.update_article.return_value = {"Body": "New body"}
    svc = PushService(db=db, tdx_client=tdx)
    svc.push(change.id)
    log = db.query(AuditLog).first()
    assert log is not None
    assert log.tdx_id == 55
    assert log.new_body == "New body"
    assert log.action == "update"

def test_push_updates_article_body_in_db(db):
    change = seed_approved_change(db)
    tdx = MagicMock()
    tdx.update_article.return_value = {"Body": "New body"}
    svc = PushService(db=db, tdx_client=tdx)
    svc.push(change.id)
    article = db.query(Article).filter_by(tdx_id=55).first()
    assert article.body == "New body"
```

**Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_push_service.py -v
```
Expected: FAIL

**Step 3: Implement PushService**

```python
# backend/services/push_service.py
from datetime import datetime
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
            change.pushed_at = datetime.utcnow()
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
```

**Step 4: Run tests to confirm they pass**

```bash
python -m pytest tests/test_push_service.py -v
```
Expected: All PASS

**Step 5: Commit**

```bash
git add backend/services/push_service.py backend/tests/test_push_service.py
git commit -m "feat: add TDX write-back push service with audit logging"
```

---

## Phase 5: FastAPI Routers

### Task 12: Articles router

**Files:**
- Create: `backend/routers/__init__.py`
- Create: `backend/routers/articles.py`
- Create: `backend/tests/test_router_articles.py`
- Modify: `backend/main.py`

**Step 1: Write failing tests**

```python
# backend/tests/test_router_articles.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from models import Base, Article
from main import app
from database import get_db

@pytest.fixture
def client_with_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    def override_db():
        with Session(engine) as session:
            yield session
    app.dependency_overrides[get_db] = override_db
    # Seed one article
    with Session(engine) as s:
        s.add(Article(tdx_id=1, title="Test", body="Body",
                      category_id=1, category_name="Cat",
                      heuristic_score=7.0, status="active"))
        s.commit()
    yield TestClient(app)
    app.dependency_overrides.clear()

def test_list_articles(client_with_db):
    response = client_with_db.get("/api/articles")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Test"

def test_get_article(client_with_db):
    response = client_with_db.get("/api/articles/1")
    assert response.status_code == 200
    assert response.json()["tdx_id"] == 1

def test_get_article_not_found(client_with_db):
    response = client_with_db.get("/api/articles/999")
    assert response.status_code == 404
```

**Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_router_articles.py -v
```
Expected: FAIL

**Step 3: Implement articles router**

```python
# backend/routers/__init__.py
# (empty)

# backend/routers/articles.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Article

router = APIRouter(prefix="/api/articles", tags=["articles"])

@router.get("")
def list_articles(
    status: str | None = None,
    category_id: int | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(Article)
    if status:
        q = q.filter(Article.status == status)
    if category_id:
        q = q.filter(Article.category_id == category_id)
    return q.order_by(Article.heuristic_score).all()

@router.get("/{article_id}")
def get_article(article_id: int, db: Session = Depends(get_db)):
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article
```

Add to `backend/main.py`:

```python
from routers import articles
app.include_router(articles.router)
```

**Step 4: Run tests to confirm they pass**

```bash
python -m pytest tests/test_router_articles.py -v
```
Expected: All PASS

**Step 5: Commit**

```bash
git add backend/routers/ backend/main.py backend/tests/test_router_articles.py
git commit -m "feat: add articles REST router"
```

---

### Task 13: Queue router

**Files:**
- Create: `backend/routers/queue.py`
- Create: `backend/tests/test_router_queue.py`
- Modify: `backend/main.py`

**Step 1: Write failing tests**

```python
# backend/tests/test_router_queue.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from models import Base, Article, AnalysisResult, ReviewQueue
from main import app
from database import get_db

@pytest.fixture
def client_with_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    def override_db():
        with Session(engine) as session:
            yield session
    app.dependency_overrides[get_db] = override_db
    with Session(engine) as s:
        art = Article(tdx_id=1, title="Art", body="Old",
                      category_id=1, category_name="Cat",
                      heuristic_score=4.0, status="active")
        s.add(art)
        s.flush()
        ana = AnalysisResult(
            article_id=art.id, model_used="test",
            score_clarity=6.0, score_completeness=6.0,
            score_findability=6.0, score_redundancy=6.0, score_accuracy=6.0,
            overall_score=6.0, issue_summary="Issues", defects_json="[]",
            proposed_body="Better", approval_tier="confirm",
        )
        s.add(ana)
        s.flush()
        s.add(ReviewQueue(article_id=art.id, analysis_id=ana.id))
        s.commit()
    yield TestClient(app)
    app.dependency_overrides.clear()

def test_list_queue(client_with_db):
    response = client_with_db.get("/api/queue")
    assert response.status_code == 200
    assert len(response.json()) == 1

def test_approve_queue_item(client_with_db):
    response = client_with_db.post("/api/queue/1/approve")
    assert response.status_code == 200
    assert response.json()["status"] == "approved"

def test_reject_queue_item(client_with_db):
    response = client_with_db.post("/api/queue/1/reject",
                                   json={"note": "Not needed"})
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
```

**Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_router_queue.py -v
```
Expected: FAIL

**Step 3: Implement queue router**

```python
# backend/routers/queue.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models import ReviewQueue
from services.approval import ApprovalService

router = APIRouter(prefix="/api/queue", tags=["queue"])

class ApproveRequest(BaseModel):
    edited_body: str | None = None

class RejectRequest(BaseModel):
    note: str = ""

@router.get("")
def list_queue(status: str = "pending", db: Session = Depends(get_db)):
    return (
        db.query(ReviewQueue)
        .filter(ReviewQueue.status == status)
        .order_by(ReviewQueue.queued_at)
        .all()
    )

@router.post("/{item_id}/approve")
def approve(item_id: int, req: ApproveRequest = ApproveRequest(),
            db: Session = Depends(get_db)):
    svc = ApprovalService(db=db)
    try:
        svc.approve(queue_item_id=item_id, edited_body=req.edited_body)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return db.get(ReviewQueue, item_id)

@router.post("/{item_id}/reject")
def reject(item_id: int, req: RejectRequest, db: Session = Depends(get_db)):
    svc = ApprovalService(db=db)
    try:
        svc.reject(queue_item_id=item_id, note=req.note)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return db.get(ReviewQueue, item_id)

@router.post("/{item_id}/skip")
def skip(item_id: int, db: Session = Depends(get_db)):
    svc = ApprovalService(db=db)
    try:
        svc.skip(queue_item_id=item_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return db.get(ReviewQueue, item_id)
```

Add to `backend/main.py`:

```python
from routers import queue
app.include_router(queue.router)
```

**Step 4: Run tests to confirm they pass**

```bash
python -m pytest tests/test_router_queue.py -v
```
Expected: All PASS

**Step 5: Commit**

```bash
git add backend/routers/queue.py backend/main.py backend/tests/test_router_queue.py
git commit -m "feat: add queue router with approve/reject/skip endpoints"
```

---

### Task 14: Scans router

**Files:**
- Create: `backend/routers/scans.py`
- Create: `backend/tests/test_router_scans.py`
- Modify: `backend/main.py`

**Step 1: Write failing tests**

```python
# backend/tests/test_router_scans.py
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from models import Base, ScanJob
from main import app
from database import get_db

@pytest.fixture
def client_with_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    def override_db():
        with Session(engine) as session:
            yield session
    app.dependency_overrides[get_db] = override_db
    yield TestClient(app)
    app.dependency_overrides.clear()

def test_list_scan_jobs_empty(client_with_db):
    response = client_with_db.get("/api/scans")
    assert response.status_code == 200
    assert response.json() == []

def test_trigger_full_batch_scan(client_with_db):
    mock_job = MagicMock()
    mock_job.id = 1
    mock_job.mode = "full_batch"
    mock_job.status = "complete"
    mock_job.articles_scanned = 10
    mock_job.articles_flagged = 3
    with patch("routers.scans.run_scan_job", return_value=mock_job):
        response = client_with_db.post("/api/scans/trigger", json={"mode": "full_batch"})
    assert response.status_code == 200
    assert response.json()["mode"] == "full_batch"
```

**Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_router_scans.py -v
```
Expected: FAIL

**Step 3: Implement scans router**

```python
# backend/routers/scans.py
from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models import ScanJob

router = APIRouter(prefix="/api/scans", tags=["scans"])

def run_scan_job(mode: str, db: Session):
    """Injected at startup with real TDX+Claude dependencies."""
    raise NotImplementedError("run_scan_job must be injected via app state")

class TriggerRequest(BaseModel):
    mode: str = "heuristic"  # heuristic | full_batch

@router.get("")
def list_scans(db: Session = Depends(get_db)):
    return db.query(ScanJob).order_by(ScanJob.started_at.desc()).limit(50).all()

@router.post("/trigger")
def trigger_scan(req: TriggerRequest, db: Session = Depends(get_db)):
    job = run_scan_job(mode=req.mode, db=db)
    return job
```

Add to `backend/main.py` after imports:

```python
from routers import scans
app.include_router(scans.router)
```

**Step 4: Run tests**

```bash
python -m pytest tests/test_router_scans.py -v
```
Expected: All PASS

**Step 5: Commit**

```bash
git add backend/routers/scans.py backend/main.py backend/tests/test_router_scans.py
git commit -m "feat: add scans router with trigger and list endpoints"
```

---

### Task 15: Audit router

**Files:**
- Create: `backend/routers/audit.py`
- Create: `backend/tests/test_router_audit.py`
- Modify: `backend/main.py`

**Step 1: Write failing tests**

```python
# backend/tests/test_router_audit.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from datetime import datetime
from models import Base, Article, AuditLog
from main import app
from database import get_db

@pytest.fixture
def client_with_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    def override_db():
        with Session(engine) as session:
            yield session
    app.dependency_overrides[get_db] = override_db
    with Session(engine) as s:
        art = Article(tdx_id=10, title="Art", body="Body",
                      category_id=1, category_name="Cat",
                      heuristic_score=8.0, status="active")
        s.add(art)
        s.flush()
        s.add(AuditLog(
            article_id=art.id, tdx_id=10, action="update",
            original_body="Old", new_body="New",
            approved_at=datetime.utcnow(),
        ))
        s.commit()
    yield TestClient(app)
    app.dependency_overrides.clear()

def test_list_audit_log(client_with_db):
    response = client_with_db.get("/api/audit")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["action"] == "update"
```

**Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_router_audit.py -v
```
Expected: FAIL

**Step 3: Implement audit router**

```python
# backend/routers/audit.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import AuditLog

router = APIRouter(prefix="/api/audit", tags=["audit"])

@router.get("")
def list_audit(limit: int = 100, db: Session = Depends(get_db)):
    return (
        db.query(AuditLog)
        .order_by(AuditLog.pushed_at.desc())
        .limit(limit)
        .all()
    )
```

Add to `backend/main.py`:

```python
from routers import audit
app.include_router(audit.router)
```

**Step 4: Run tests**

```bash
python -m pytest tests/test_router_audit.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add backend/routers/audit.py backend/main.py backend/tests/test_router_audit.py
git commit -m "feat: add audit log router"
```

---

## Phase 6: Scheduler

### Task 16: APScheduler integration

**Files:**
- Create: `backend/scheduler.py`
- Modify: `backend/main.py`

**Step 1: Implement scheduler.py**

```python
# backend/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = BackgroundScheduler()

def start_scheduler(cron_expression: str, job_fn):
    parts = cron_expression.split()
    trigger = CronTrigger(
        minute=parts[0], hour=parts[1],
        day=parts[2], month=parts[3], day_of_week=parts[4],
    )
    scheduler.add_job(job_fn, trigger=trigger, id="heuristic_scan",
                      replace_existing=True)
    scheduler.start()

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
```

**Step 2: Wire scheduler into main.py**

Add startup/shutdown events to `backend/main.py`:

```python
from contextlib import asynccontextmanager
from config import get_settings
from database import SessionLocal
from services.tdx_client import TDXClient
from services.claude_client import ClaudeAnalyzer
from services.scan_engine import ScanEngine
from scheduler import start_scheduler, stop_scheduler
import routers.scans as scans_router

@asynccontextmanager
async def lifespan(app_: FastAPI):
    settings = get_settings()
    tdx = TDXClient(
        base_url=settings.tdx_base_url,
        app_id=settings.tdx_app_id,
        beid=settings.tdx_beid,
        web_services_key=settings.tdx_web_services_key,
    )
    analyzer = ClaudeAnalyzer(
        api_key=settings.anthropic_api_key,
        model=settings.claude_model,
    )

    def run_scan(mode: str = "heuristic", db=None):
        with SessionLocal() as session:
            engine = ScanEngine(db=session, tdx_client=tdx, analyzer=analyzer,
                                heuristic_threshold=settings.heuristic_threshold)
            if mode == "full_batch":
                return engine.run_full_batch_scan()
            return engine.run_heuristic_scan()

    scans_router.run_scan_job = run_scan
    start_scheduler(settings.scan_cron, lambda: run_scan("heuristic"))
    yield
    stop_scheduler()

# Update app instantiation to use lifespan:
app = FastAPI(title="TDX KA Fixer", version="0.1.0", lifespan=lifespan)
```

**Step 3: Run full test suite**

```bash
python -m pytest tests/ -v
```
Expected: All PASS

**Step 4: Confirm app starts with scheduler**

```bash
uvicorn main:app --reload --port 8000
```
Expected: Server starts, no errors. Visit http://127.0.0.1:8000/docs.

**Step 5: Commit**

```bash
git add backend/scheduler.py backend/main.py
git commit -m "feat: integrate APScheduler for background heuristic scans"
```

---

## Phase 7: Frontend Foundation

### Task 17: Vite + React + TypeScript scaffold

**Files:**
- Create: `frontend/` (via Vite CLI)

**Step 1: Scaffold the frontend**

```bash
cd /path/to/tdx-ka-fixer
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

**Step 2: Install additional dependencies**

```bash
npm install react-router-dom @tanstack/react-query axios react-diff-viewer-continued
npm install -D @types/react-router-dom
```

**Step 3: Configure Vite proxy**

Edit `frontend/vite.config.ts`:

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
```

**Step 4: Confirm frontend starts**

```bash
npm run dev
```
Expected: Vite dev server at http://localhost:5173

**Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold React+TypeScript frontend with Vite"
```

---

### Task 18: API client layer

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/articles.ts`
- Create: `frontend/src/api/queue.ts`
- Create: `frontend/src/api/scans.ts`
- Create: `frontend/src/api/audit.ts`
- Create: `frontend/src/api/types.ts`

**Step 1: Define shared types**

```typescript
// frontend/src/api/types.ts
export interface Article {
  id: number
  tdx_id: number
  title: string
  body: string
  category_id: number
  category_name: string
  modified_at: string | null
  heuristic_score: number
  status: string
}

export interface AnalysisResult {
  id: number
  article_id: number
  overall_score: number
  score_clarity: number
  score_completeness: number
  score_findability: number
  score_redundancy: number
  score_accuracy: number
  issue_summary: string
  defects_json: string
  proposed_body: string
  approval_tier: 'auto' | 'confirm' | 'admin'
  analyzed_at: string
}

export interface QueueItem {
  id: number
  article_id: number
  analysis_id: number
  status: 'pending' | 'approved' | 'rejected' | 'skipped'
  queued_at: string
  reviewed_at: string | null
  reviewer_note: string | null
  article: Article
  analysis: AnalysisResult
}

export interface ScanJob {
  id: number
  mode: 'heuristic' | 'full_batch'
  status: 'running' | 'complete' | 'failed'
  started_at: string
  completed_at: string | null
  articles_scanned: number
  articles_flagged: number
}

export interface AuditEntry {
  id: number
  tdx_id: number
  article_id: number
  action: string
  original_body: string
  new_body: string
  pushed_at: string
}
```

**Step 2: Create base axios client**

```typescript
// frontend/src/api/client.ts
import axios from 'axios'

const client = axios.create({ baseURL: '/api' })
export default client
```

**Step 3: Create API modules**

```typescript
// frontend/src/api/articles.ts
import client from './client'
import type { Article } from './types'

export const listArticles = (params?: { status?: string; category_id?: number }) =>
  client.get<Article[]>('/articles', { params }).then(r => r.data)

export const getArticle = (id: number) =>
  client.get<Article>(`/articles/${id}`).then(r => r.data)
```

```typescript
// frontend/src/api/queue.ts
import client from './client'
import type { QueueItem } from './types'

export const listQueue = (status = 'pending') =>
  client.get<QueueItem[]>('/queue', { params: { status } }).then(r => r.data)

export const approveItem = (id: number, editedBody?: string) =>
  client.post<QueueItem>(`/queue/${id}/approve`, { edited_body: editedBody }).then(r => r.data)

export const rejectItem = (id: number, note = '') =>
  client.post<QueueItem>(`/queue/${id}/reject`, { note }).then(r => r.data)

export const skipItem = (id: number) =>
  client.post<QueueItem>(`/queue/${id}/skip`).then(r => r.data)
```

```typescript
// frontend/src/api/scans.ts
import client from './client'
import type { ScanJob } from './types'

export const listScans = () =>
  client.get<ScanJob[]>('/scans').then(r => r.data)

export const triggerScan = (mode: 'heuristic' | 'full_batch') =>
  client.post<ScanJob>('/scans/trigger', { mode }).then(r => r.data)
```

```typescript
// frontend/src/api/audit.ts
import client from './client'
import type { AuditEntry } from './types'

export const listAudit = (limit = 100) =>
  client.get<AuditEntry[]>('/audit', { params: { limit } }).then(r => r.data)
```

**Step 4: Commit**

```bash
git add frontend/src/api/
git commit -m "feat: add typed API client layer for all backend endpoints"
```

---

### Task 19: App layout and routing

**Files:**
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/main.tsx` (modify)
- Create: `frontend/src/components/Layout.tsx`

**Step 1: Create Layout component**

```tsx
// frontend/src/components/Layout.tsx
import { NavLink, Outlet } from 'react-router-dom'

const nav = [
  { to: '/', label: 'Dashboard' },
  { to: '/browser', label: 'Article Browser' },
  { to: '/queue', label: 'Review Queue' },
  { to: '/audit', label: 'Audit Log' },
  { to: '/settings', label: 'Settings' },
]

export default function Layout() {
  return (
    <div style={{ display: 'flex', minHeight: '100vh', fontFamily: 'sans-serif' }}>
      <nav style={{ width: 200, background: '#1e293b', color: '#fff', padding: 16 }}>
        <h2 style={{ color: '#60a5fa', marginTop: 0 }}>TDX KA Fixer</h2>
        {nav.map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            style={({ isActive }) => ({
              display: 'block',
              padding: '8px 12px',
              color: isActive ? '#60a5fa' : '#cbd5e1',
              textDecoration: 'none',
              borderRadius: 4,
              marginBottom: 4,
              background: isActive ? '#0f172a' : 'transparent',
            })}
          >
            {label}
          </NavLink>
        ))}
      </nav>
      <main style={{ flex: 1, padding: 24, background: '#f8fafc' }}>
        <Outlet />
      </main>
    </div>
  )
}
```

**Step 2: Create App.tsx with routes**

```tsx
// frontend/src/App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Layout from './components/Layout'
import Dashboard from './views/Dashboard'
import ArticleBrowser from './views/ArticleBrowser'
import ReviewQueue from './views/ReviewQueue'
import AuditLogView from './views/AuditLogView'
import SettingsView from './views/Settings'

const queryClient = new QueryClient()

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="browser" element={<ArticleBrowser />} />
            <Route path="queue" element={<ReviewQueue />} />
            <Route path="audit" element={<AuditLogView />} />
            <Route path="settings" element={<SettingsView />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
```

**Step 3: Create placeholder views so app compiles**

Create `frontend/src/views/Dashboard.tsx`, `ArticleBrowser.tsx`, `ReviewQueue.tsx`, `AuditLogView.tsx`, `Settings.tsx`, each as:

```tsx
export default function Dashboard() { return <div><h1>Dashboard</h1></div> }
```
(Substitute function name and heading for each file.)

**Step 4: Confirm frontend compiles and nav works**

```bash
npm run dev
```
Expected: App loads at http://localhost:5173, nav links work.

**Step 5: Commit**

```bash
git add frontend/src/
git commit -m "feat: add app routing and nav layout"
```

---

## Phase 8: Frontend Views

### Task 20: Dashboard view

**Files:**
- Modify: `frontend/src/views/Dashboard.tsx`

**Step 1: Implement Dashboard**

```tsx
// frontend/src/views/Dashboard.tsx
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listScans, triggerScan } from '../api/scans'
import { listQueue } from '../api/queue'

export default function Dashboard() {
  const qc = useQueryClient()
  const { data: scans } = useQuery({ queryKey: ['scans'], queryFn: listScans })
  const { data: pending } = useQuery({ queryKey: ['queue', 'pending'], queryFn: () => listQueue('pending') })
  const { data: approved } = useQuery({ queryKey: ['queue', 'approved'], queryFn: () => listQueue('approved') })

  const trigger = useMutation({
    mutationFn: triggerScan,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['scans'] }),
  })

  const lastScan = scans?.[0]

  return (
    <div>
      <h1>Dashboard</h1>
      <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
        <StatCard label="Pending Review" value={pending?.length ?? 0} />
        <StatCard label="Approved (not pushed)" value={approved?.length ?? 0} />
        <StatCard label="Total Scans" value={scans?.length ?? 0} />
      </div>

      <section>
        <h2>Last Scan</h2>
        {lastScan ? (
          <p>
            Mode: <strong>{lastScan.mode}</strong> &nbsp;|&nbsp;
            Status: <strong>{lastScan.status}</strong> &nbsp;|&nbsp;
            Scanned: {lastScan.articles_scanned} &nbsp;|&nbsp;
            Flagged: {lastScan.articles_flagged} &nbsp;|&nbsp;
            At: {new Date(lastScan.started_at).toLocaleString()}
          </p>
        ) : <p>No scans yet.</p>}
      </section>

      <section style={{ marginTop: 24 }}>
        <h2>Trigger Scan</h2>
        <button
          onClick={() => trigger.mutate('heuristic')}
          disabled={trigger.isPending}
          style={{ marginRight: 12, padding: '8px 16px' }}
        >
          Run Heuristic Scan
        </button>
        <button
          onClick={() => trigger.mutate('full_batch')}
          disabled={trigger.isPending}
          style={{ padding: '8px 16px' }}
        >
          Run Full Batch Scan
        </button>
        {trigger.isPending && <span style={{ marginLeft: 12 }}>Running...</span>}
      </section>
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div style={{
      background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8,
      padding: '16px 24px', minWidth: 160, textAlign: 'center',
    }}>
      <div style={{ fontSize: 32, fontWeight: 700, color: '#1e293b' }}>{value}</div>
      <div style={{ color: '#64748b', fontSize: 14 }}>{label}</div>
    </div>
  )
}
```

**Step 2: Verify in browser**

Start both servers and confirm Dashboard loads with stat cards and scan buttons.

**Step 3: Commit**

```bash
git add frontend/src/views/Dashboard.tsx
git commit -m "feat: implement dashboard view with scan controls and stats"
```

---

### Task 21: Article browser view

**Files:**
- Modify: `frontend/src/views/ArticleBrowser.tsx`

**Step 1: Implement ArticleBrowser**

```tsx
// frontend/src/views/ArticleBrowser.tsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listArticles } from '../api/articles'

export default function ArticleBrowser() {
  const [search, setSearch] = useState('')
  const { data: articles, isLoading } = useQuery({
    queryKey: ['articles'],
    queryFn: () => listArticles(),
  })

  const filtered = articles?.filter(a =>
    a.title.toLowerCase().includes(search.toLowerCase()) ||
    a.category_name.toLowerCase().includes(search.toLowerCase())
  ) ?? []

  return (
    <div>
      <h1>Article Browser</h1>
      <input
        placeholder="Search by title or category..."
        value={search}
        onChange={e => setSearch(e.target.value)}
        style={{ padding: '8px 12px', width: 360, marginBottom: 16, fontSize: 14 }}
      />
      {isLoading && <p>Loading...</p>}
      <table style={{ width: '100%', borderCollapse: 'collapse', background: '#fff' }}>
        <thead>
          <tr style={{ background: '#f1f5f9' }}>
            <th style={th}>Title</th>
            <th style={th}>Category</th>
            <th style={th}>Heuristic Score</th>
            <th style={th}>Status</th>
            <th style={th}>Modified</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map(a => (
            <tr key={a.id} style={{ borderBottom: '1px solid #e2e8f0' }}>
              <td style={td}>{a.title}</td>
              <td style={td}>{a.category_name}</td>
              <td style={td}>
                <span style={{ color: a.heuristic_score < 5 ? '#ef4444' : '#16a34a' }}>
                  {a.heuristic_score.toFixed(1)}
                </span>
              </td>
              <td style={td}>{a.status}</td>
              <td style={td}>{a.modified_at ? new Date(a.modified_at).toLocaleDateString() : '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {filtered.length === 0 && !isLoading && <p>No articles found.</p>}
    </div>
  )
}

const th: React.CSSProperties = { padding: '10px 14px', textAlign: 'left', fontWeight: 600, fontSize: 13 }
const td: React.CSSProperties = { padding: '10px 14px', fontSize: 14 }
```

**Step 2: Commit**

```bash
git add frontend/src/views/ArticleBrowser.tsx
git commit -m "feat: implement article browser view with search and scoring"
```

---

### Task 22: Review queue with diff viewer

**Files:**
- Modify: `frontend/src/views/ReviewQueue.tsx`
- Create: `frontend/src/components/DiffReview.tsx`

**Step 1: Create DiffReview component**

```tsx
// frontend/src/components/DiffReview.tsx
import ReactDiffViewer from 'react-diff-viewer-continued'
import type { QueueItem } from '../api/types'

interface Props {
  item: QueueItem
  onApprove: (id: number, editedBody?: string) => void
  onReject: (id: number, note: string) => void
  onSkip: (id: number) => void
}

export default function DiffReview({ item, onApprove, onReject, onSkip }: Props) {
  const tierColor = { auto: '#16a34a', confirm: '#d97706', admin: '#dc2626' }[item.analysis.approval_tier] ?? '#64748b'
  const defects: string[] = JSON.parse(item.analysis.defects_json || '[]')

  return (
    <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, padding: 24, marginBottom: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
        <div>
          <h2 style={{ margin: 0 }}>{item.article.title}</h2>
          <span style={{ fontSize: 12, color: '#64748b' }}>
            Category: {item.article.category_name} &nbsp;|&nbsp;
            Overall score: <strong>{item.analysis.overall_score.toFixed(1)}</strong>
          </span>
        </div>
        <span style={{
          background: tierColor, color: '#fff',
          padding: '4px 10px', borderRadius: 12, fontSize: 12, fontWeight: 600,
        }}>
          {item.analysis.approval_tier.toUpperCase()}
        </span>
      </div>

      <p style={{ color: '#374151', marginBottom: 8 }}><strong>Issues:</strong> {item.analysis.issue_summary}</p>
      {defects.length > 0 && (
        <ul style={{ color: '#6b7280', fontSize: 13, marginBottom: 16 }}>
          {defects.map((d, i) => <li key={i}>{d}</li>)}
        </ul>
      )}

      <ReactDiffViewer
        oldValue={item.article.body}
        newValue={item.analysis.proposed_body}
        splitView={true}
        leftTitle="Current"
        rightTitle="Proposed"
      />

      <div style={{ display: 'flex', gap: 12, marginTop: 16 }}>
        <button
          onClick={() => onApprove(item.id)}
          style={{ padding: '8px 20px', background: '#16a34a', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' }}
        >
          Approve
        </button>
        <button
          onClick={() => {
            const note = window.prompt('Rejection reason (optional):') ?? ''
            onReject(item.id, note)
          }}
          style={{ padding: '8px 20px', background: '#dc2626', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' }}
        >
          Reject
        </button>
        <button
          onClick={() => onSkip(item.id)}
          style={{ padding: '8px 20px', background: '#64748b', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' }}
        >
          Skip
        </button>
      </div>
    </div>
  )
}
```

**Step 2: Implement ReviewQueue view**

```tsx
// frontend/src/views/ReviewQueue.tsx
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listQueue, approveItem, rejectItem, skipItem } from '../api/queue'
import DiffReview from '../components/DiffReview'

export default function ReviewQueue() {
  const qc = useQueryClient()
  const { data: items, isLoading } = useQuery({
    queryKey: ['queue', 'pending'],
    queryFn: () => listQueue('pending'),
  })

  const invalidate = () => qc.invalidateQueries({ queryKey: ['queue'] })

  const approve = useMutation({ mutationFn: ({ id, body }: { id: number; body?: string }) => approveItem(id, body), onSuccess: invalidate })
  const reject = useMutation({ mutationFn: ({ id, note }: { id: number; note: string }) => rejectItem(id, note), onSuccess: invalidate })
  const skip = useMutation({ mutationFn: skipItem, onSuccess: invalidate })

  if (isLoading) return <p>Loading queue...</p>

  return (
    <div>
      <h1>Review Queue <span style={{ fontSize: 16, color: '#64748b' }}>({items?.length ?? 0} pending)</span></h1>
      {items?.length === 0 && <p>Queue is empty.</p>}
      {items?.map(item => (
        <DiffReview
          key={item.id}
          item={item}
          onApprove={(id, body) => approve.mutate({ id, body })}
          onReject={(id, note) => reject.mutate({ id, note })}
          onSkip={id => skip.mutate(id)}
        />
      ))}
    </div>
  )
}
```

**Step 3: Commit**

```bash
git add frontend/src/views/ReviewQueue.tsx frontend/src/components/DiffReview.tsx
git commit -m "feat: implement review queue with side-by-side diff viewer"
```

---

### Task 23: Audit log view

**Files:**
- Modify: `frontend/src/views/AuditLogView.tsx`

**Step 1: Implement AuditLogView**

```tsx
// frontend/src/views/AuditLogView.tsx
import { useQuery } from '@tanstack/react-query'
import { listAudit } from '../api/audit'

export default function AuditLogView() {
  const { data: entries, isLoading } = useQuery({
    queryKey: ['audit'],
    queryFn: () => listAudit(100),
  })

  return (
    <div>
      <h1>Audit Log</h1>
      {isLoading && <p>Loading...</p>}
      <table style={{ width: '100%', borderCollapse: 'collapse', background: '#fff' }}>
        <thead>
          <tr style={{ background: '#f1f5f9' }}>
            <th style={th}>TDX ID</th>
            <th style={th}>Action</th>
            <th style={th}>Pushed At</th>
          </tr>
        </thead>
        <tbody>
          {entries?.map(e => (
            <tr key={e.id} style={{ borderBottom: '1px solid #e2e8f0' }}>
              <td style={td}>{e.tdx_id}</td>
              <td style={td}>{e.action}</td>
              <td style={td}>{new Date(e.pushed_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {entries?.length === 0 && !isLoading && <p>No changes pushed yet.</p>}
    </div>
  )
}

const th: React.CSSProperties = { padding: '10px 14px', textAlign: 'left', fontWeight: 600, fontSize: 13 }
const td: React.CSSProperties = { padding: '10px 14px', fontSize: 14 }
```

**Step 2: Commit**

```bash
git add frontend/src/views/AuditLogView.tsx
git commit -m "feat: implement audit log view"
```

---

### Task 24: Settings view

**Files:**
- Modify: `frontend/src/views/Settings.tsx`

**Step 1: Implement Settings view**

```tsx
// frontend/src/views/Settings.tsx
export default function Settings() {
  return (
    <div>
      <h1>Settings</h1>
      <p style={{ color: '#64748b' }}>
        All credentials and configuration are managed via the <code>.env</code> file
        in the project root. Restart the backend after making changes.
      </p>
      <table style={{ borderCollapse: 'collapse', fontSize: 14 }}>
        <tbody>
          {[
            ['ANTHROPIC_API_KEY', 'Anthropic API key for Claude analysis'],
            ['TDX_BASE_URL', 'TeamDynamix instance base URL'],
            ['TDX_APP_ID', 'TDX Knowledge Base application ID'],
            ['TDX_BEID', 'TDX admin BEID for API auth'],
            ['TDX_WEB_SERVICES_KEY', 'TDX admin Web Services Key'],
            ['SCAN_CRON', 'Cron expression for heuristic scan schedule (default: 0 2 * * *)'],
            ['HEURISTIC_THRESHOLD', 'Score below which articles are flagged (default: 5.0)'],
            ['CLAUDE_MODEL', 'Claude model to use (default: claude-sonnet-4-6)'],
          ].map(([key, desc]) => (
            <tr key={key} style={{ borderBottom: '1px solid #e2e8f0' }}>
              <td style={{ padding: '10px 16px 10px 0', fontFamily: 'monospace', fontWeight: 600 }}>{key}</td>
              <td style={{ padding: '10px 0', color: '#64748b' }}>{desc}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

**Step 2: Commit**

```bash
git add frontend/src/views/Settings.tsx
git commit -m "feat: implement settings view with env variable reference"
```

---

## Phase 9: Final Integration

### Task 25: Run full backend test suite and fix any failures

**Step 1: Run all backend tests**

```bash
cd backend && python -m pytest tests/ -v --tb=short
```
Expected: All PASS

**Step 2: If any failures, fix them before proceeding**

**Step 3: Run frontend build check**

```bash
cd frontend && npm run build
```
Expected: Build succeeds with no TypeScript errors.

**Step 4: Smoke test end-to-end**

1. Copy `.env.example` to `.env` and fill in real credentials (TDX + fresh Anthropic API key)
2. Start backend: `cd backend && uvicorn main:app --reload --port 8000`
3. Start frontend: `cd frontend && npm run dev`
4. Open http://localhost:5173
5. Navigate to Dashboard and trigger a Heuristic Scan
6. Verify scan completes and articles appear in the Review Queue
7. Review one article in the diff view, approve it
8. Verify the change appears in the Audit Log

**Step 5: Commit any final fixes**

```bash
git add -A
git commit -m "fix: integration fixes from end-to-end smoke test"
```

---

## Running the App

```bash
# Terminal 1 — Backend
cd backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm run dev
```

Open http://localhost:5173

> **Note on TDX API endpoints:** The exact TDX REST API paths (`/knowledgebase/search`, field names like `Subject`, `Body`, `ID`, etc.) should be verified against your institution's TDX API documentation at `{TDX_BASE_URL}/api/docs`. Adjust `backend/services/tdx_client.py` field mappings if needed.
