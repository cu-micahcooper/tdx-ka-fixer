# Configurable AI Directives Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Move hardcoded Claude institutional context out of `claude_client.py` into a DB-backed setting with separate directives for internal vs. public articles, editable via the Settings UI.

**Architecture:** New `AppSettings` model (single row, id=1) stores `internal_directive` and `public_directive` text. A new `/api/settings` router serves GET (seeds defaults on first use) and PATCH. `ClaudeAnalyzer.analyze()` gains a `directive` parameter injected into the prompt. `ScanEngine` loads the right directive from DB and passes it through. Settings UI adds two interactive textareas with a Save button.

**Tech Stack:** FastAPI + SQLAlchemy + SQLite (backend), React + TypeScript + native fetch (frontend)

---

### Task 1: Add AppSettings model

**Files:**
- Modify: `backend/models.py`
- Test: `backend/tests/test_models.py`

**Step 1: Write the failing test**

Add to `backend/tests/test_models.py`:

```python
from models import AppSettings

def test_app_settings_defaults(db_session):
    row = AppSettings()
    db_session.add(row)
    db_session.commit()
    assert row.id is not None
    assert row.internal_directive == ""
    assert row.public_directive == ""
```

Note: `db_session` fixture already exists in `test_models.py` — check the top of that file for the fixture definition and reuse it.

**Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_models.py::test_app_settings_defaults -v
```
Expected: FAIL — `cannot import name 'AppSettings' from 'models'`

**Step 3: Add the model**

Add to `backend/models.py`, after the `ScanJob` class:

```python
class AppSettings(Base):
    __tablename__ = "app_settings"
    id = Column(Integer, primary_key=True)
    internal_directive = Column(Text, nullable=False, default="")
    public_directive = Column(Text, nullable=False, default="")
```

**Step 4: Run test to verify it passes**

```bash
cd backend && python -m pytest tests/test_models.py::test_app_settings_defaults -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add backend/models.py backend/tests/test_models.py
git commit -m "feat: add AppSettings model for configurable AI directives"
```

---

### Task 2: Create settings router

**Files:**
- Create: `backend/routers/settings.py`
- Create: `backend/tests/test_router_settings.py`
- Modify: `backend/main.py`

**Step 1: Write the failing tests**

Create `backend/tests/test_router_settings.py`:

```python
# backend/tests/test_router_settings.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from models import Base
from main import app
from database import get_db


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    def override_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_get_settings_seeds_defaults(client):
    """First GET creates a row and returns non-empty defaults."""
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert "internal_directive" in data
    assert "public_directive" in data
    # Defaults should be pre-populated with Cedarville context
    assert len(data["internal_directive"]) > 50
    assert len(data["public_directive"]) > 50


def test_get_settings_is_idempotent(client):
    """Two GETs return identical data and don't create duplicate rows."""
    r1 = client.get("/api/settings")
    r2 = client.get("/api/settings")
    assert r1.json() == r2.json()


def test_patch_settings_updates_directives(client):
    client.get("/api/settings")  # seed
    response = client.patch(
        "/api/settings",
        json={"internal_directive": "Internal only text"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["internal_directive"] == "Internal only text"
    # public_directive unchanged
    assert len(data["public_directive"]) > 50


def test_patch_then_get_persists(client):
    client.get("/api/settings")  # seed
    client.patch("/api/settings", json={"public_directive": "Public text"})
    response = client.get("/api/settings")
    assert response.json()["public_directive"] == "Public text"


def test_patch_empty_string_allowed(client):
    client.get("/api/settings")
    response = client.patch("/api/settings", json={"internal_directive": ""})
    assert response.status_code == 200
    assert response.json()["internal_directive"] == ""
```

**Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_router_settings.py -v
```
Expected: FAIL — 404 or import error

**Step 3: Create the router**

Create `backend/routers/settings.py`:

```python
# backend/routers/settings.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models import AppSettings

router = APIRouter(prefix="/api/settings", tags=["settings"])

# Default directives pre-populated from original hardcoded prompt context.
# Users can edit these freely in the UI.
_DEFAULT_INTERNAL_DIRECTIVE = """\
This knowledge base belongs to Cedarville University — a private Christian liberal arts university in Cedarville, Ohio.
The articles support students, faculty, and staff seeking IT help.

Key facts to reflect in rewrites:
- The IT help desk uses TeamDynamix (TDX) for ticketing and this knowledge base.
- Common systems in use: Microsoft 365 (Outlook, Teams, OneDrive, SharePoint), Banner (ERP/student information), Blackboard/Canvas (LMS), Duo (MFA), GlobalProtect VPN, CU-managed Windows and Mac devices.
- Users are a campus community — write in plain, friendly language appropriate for a university help desk. Avoid jargon; define acronyms on first use.
- Links to cedarville.edu resources should be preserved and treated as authoritative.
- If scraped source content is provided, use it to ensure accuracy and completeness — do not fabricate steps or policy details.\
"""

_DEFAULT_PUBLIC_DIRECTIVE = """\
This knowledge base belongs to Cedarville University — a private Christian liberal arts university in Cedarville, Ohio.
These articles are publicly visible and may be read by prospective students, parents, or external visitors in addition to current students, faculty, and staff.

Key facts to reflect in rewrites:
- The IT help desk uses TeamDynamix (TDX) for ticketing and this knowledge base.
- Common systems in use: Microsoft 365 (Outlook, Teams, OneDrive, SharePoint), Banner (ERP/student information), Blackboard/Canvas (LMS), Duo (MFA), GlobalProtect VPN, CU-managed Windows and Mac devices.
- Write in plain, welcoming language appropriate for a broad audience. Avoid jargon; define all acronyms on first use.
- Links to cedarville.edu resources should be preserved and treated as authoritative.
- If scraped source content is provided, use it to ensure accuracy and completeness — do not fabricate steps or policy details.\
"""


def _get_or_create(db: Session) -> AppSettings:
    row = db.query(AppSettings).first()
    if row is None:
        row = AppSettings(
            internal_directive=_DEFAULT_INTERNAL_DIRECTIVE,
            public_directive=_DEFAULT_PUBLIC_DIRECTIVE,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.get("")
def get_settings(db: Session = Depends(get_db)):
    row = _get_or_create(db)
    return {
        "internal_directive": row.internal_directive,
        "public_directive": row.public_directive,
    }


class SettingsPatch(BaseModel):
    internal_directive: str | None = None
    public_directive: str | None = None


@router.patch("")
def patch_settings(body: SettingsPatch, db: Session = Depends(get_db)):
    row = _get_or_create(db)
    if body.internal_directive is not None:
        row.internal_directive = body.internal_directive
    if body.public_directive is not None:
        row.public_directive = body.public_directive
    db.commit()
    db.refresh(row)
    return {
        "internal_directive": row.internal_directive,
        "public_directive": row.public_directive,
    }
```

**Step 4: Mount the router in main.py**

In `backend/main.py`, add the import and `include_router` call.

Find this block at the bottom of `main.py`:
```python
from routers import articles, queue, scans, audit, stats
app.include_router(articles.router)
app.include_router(queue.router)
app.include_router(scans.router)
app.include_router(audit.router)
app.include_router(push_router.router)
app.include_router(stats.router)
```

Replace with:
```python
from routers import articles, queue, scans, audit, stats, settings as settings_router
app.include_router(articles.router)
app.include_router(queue.router)
app.include_router(scans.router)
app.include_router(audit.router)
app.include_router(push_router.router)
app.include_router(stats.router)
app.include_router(settings_router.router)
```

**Step 5: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_router_settings.py -v
```
Expected: All 5 PASS

**Step 6: Run full test suite to check for regressions**

```bash
cd backend && python -m pytest tests/ -v
```
Expected: 58/60 passing (53 existing + 5 new; same 2 known failures in test_tdx_client.py)

**Step 7: Commit**

```bash
git add backend/routers/settings.py backend/tests/test_router_settings.py backend/main.py
git commit -m "feat: add /api/settings router with GET and PATCH for AI directives"
```

---

### Task 3: Update ClaudeAnalyzer to accept directive parameter

**Files:**
- Modify: `backend/services/claude_client.py`
- Modify: `backend/tests/test_claude_client.py`

**Step 1: Write the failing test**

Add to `backend/tests/test_claude_client.py` (find the existing test file and append):

```python
def test_analyze_injects_directive_into_prompt(monkeypatch):
    """The directive text should appear in the prompt sent to Claude."""
    captured = {}

    class FakeMessages:
        def create(self, **kwargs):
            captured["prompt"] = kwargs["messages"][0]["content"]
            from unittest.mock import MagicMock
            msg = MagicMock()
            msg.content = [MagicMock(text='{"score_clarity":7.0,"score_completeness":7.0,"score_findability":7.0,"score_redundancy":7.0,"score_accuracy":7.0,"overall_score":7.0,"issue_summary":"ok","defects":[],"proposed_body":"<p>body</p>","approval_tier":"confirm"}')]
            return msg

    class FakeClient:
        messages = FakeMessages()

    import anthropic
    monkeypatch.setattr(anthropic, "Anthropic", lambda **kw: FakeClient())

    from services.claude_client import ClaudeAnalyzer
    analyzer = ClaudeAnalyzer(api_key="test")
    analyzer.analyze(title="T", body="B", directive="MY CUSTOM DIRECTIVE")
    assert "MY CUSTOM DIRECTIVE" in captured["prompt"]
```

**Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_claude_client.py::test_analyze_injects_directive_into_prompt -v
```
Expected: FAIL — `analyze() got an unexpected keyword argument 'directive'`

**Step 3: Update ANALYSIS_PROMPT and analyze() signature**

In `backend/services/claude_client.py`, replace the entire `ANALYSIS_PROMPT` string.

Current beginning:
```python
ANALYSIS_PROMPT = """You are a knowledge base quality analyst operating within the KCS (Knowledge-Centered Service) framework.

## Institutional Context

This knowledge base belongs to Cedarville University — a private Christian liberal arts university in Cedarville, Ohio.
The articles support students, faculty, and staff seeking IT help.

Key facts to reflect in rewrites:
- The IT help desk uses TeamDynamix (TDX) for ticketing and this knowledge base.
- Common systems in use: Microsoft 365 (Outlook, Teams, OneDrive, SharePoint), Banner (ERP/student information), Blackboard/Canvas (LMS), Duo (MFA), GlobalProtect VPN, CU-managed Windows and Mac devices.
- Users are a campus community — write in plain, friendly language appropriate for a university help desk. Avoid jargon; define acronyms on first use.
- Links to cedarville.edu resources should be preserved and treated as authoritative.
- If scraped source content is provided, use it to ensure accuracy and completeness — do not fabricate steps or policy details.

## Critical rewrite rules
```

Replace that block (from the `ANALYSIS_PROMPT = ` line through the blank line before `## Critical rewrite rules`) so it becomes:

```python
ANALYSIS_PROMPT = """You are a knowledge base quality analyst operating within the KCS (Knowledge-Centered Service) framework.

## Institutional Context

{directive}

## Critical rewrite rules
```

Leave everything else in the prompt exactly as-is (from `## Critical rewrite rules` to the end of the string). The `{title}`, `{body}`, `{sources}` placeholders remain; `{directive}` is the new addition.

Then update the `analyze` method signature and prompt formatting call.

Current:
```python
    def analyze(self, title: str, body: str) -> AnalysisResult:
```

Replace with:
```python
    def analyze(self, title: str, body: str, directive: str = "") -> AnalysisResult:
```

Current prompt format call (near the end of `analyze`):
```python
        prompt = ANALYSIS_PROMPT.format(title=title, body=body, sources=sources_block)
```

Replace with:
```python
        prompt = ANALYSIS_PROMPT.format(title=title, body=body, sources=sources_block, directive=directive)
```

**Step 4: Run test to verify it passes**

```bash
cd backend && python -m pytest tests/test_claude_client.py::test_analyze_injects_directive_into_prompt -v
```
Expected: PASS

**Step 5: Run full test suite**

```bash
cd backend && python -m pytest tests/ -v
```
Expected: Same pass count as before + 1 new passing test; no regressions.

**Step 6: Commit**

```bash
git add backend/services/claude_client.py backend/tests/test_claude_client.py
git commit -m "feat: parameterize institutional directive in Claude analysis prompt"
```

---

### Task 4: Wire directive into ScanEngine

**Files:**
- Modify: `backend/services/scan_engine.py`
- Modify: `backend/tests/test_scan_engine.py`

**Step 1: Write the failing tests**

Add to `backend/tests/test_scan_engine.py`:

```python
def test_internal_article_uses_internal_directive(db):
    """Non-public articles should pass the internal_directive to analyze()."""
    from models import AppSettings
    db.add(AppSettings(internal_directive="INTERNAL DIR", public_directive="PUBLIC DIR"))
    db.commit()

    tdx = MagicMock()
    raw = {**RAW_ARTICLE_BAD, "IsPublic": False}
    tdx.list_articles.return_value = [raw]
    analyzer = make_mock_analyzer()
    engine = ScanEngine(db=db, tdx_client=tdx, analyzer=analyzer)
    engine.run_heuristic_scan()

    _, kwargs = analyzer.analyze.call_args
    assert kwargs.get("directive") == "INTERNAL DIR"


def test_public_article_uses_public_directive(db):
    """Public articles should pass the public_directive to analyze()."""
    from models import AppSettings
    db.add(AppSettings(internal_directive="INTERNAL DIR", public_directive="PUBLIC DIR"))
    db.commit()

    tdx = MagicMock()
    raw = {**RAW_ARTICLE_BAD, "IsPublic": True}
    tdx.list_articles.return_value = [raw]
    analyzer = make_mock_analyzer()
    engine = ScanEngine(db=db, tdx_client=tdx, analyzer=analyzer)
    engine.run_heuristic_scan()

    _, kwargs = analyzer.analyze.call_args
    assert kwargs.get("directive") == "PUBLIC DIR"


def test_missing_settings_row_uses_empty_directive(db):
    """If AppSettings row doesn't exist, analyze() is called with directive=''."""
    tdx = MagicMock()
    tdx.list_articles.return_value = [RAW_ARTICLE_BAD]
    analyzer = make_mock_analyzer()
    engine = ScanEngine(db=db, tdx_client=tdx, analyzer=analyzer)
    engine.run_heuristic_scan()

    _, kwargs = analyzer.analyze.call_args
    assert kwargs.get("directive") == ""
```

Note: `RAW_ARTICLE_BAD` doesn't have `IsPublic`, so it defaults to `False` (internal). Add `"IsPublic": False` to `RAW_ARTICLE_BAD` at the top of the test file:
```python
RAW_ARTICLE_BAD = {
    "ID": 1, "Subject": "Article 1", "Body": "TODO: fix this",
    "CategoryID": 1, "CategoryName": "Cat",
    "CreatedDate": "2023-01-01T00:00:00Z",
    "ModifiedDate": "2023-01-01T00:00:00Z",
    "NumViews": 2, "IsActive": True, "IsPublic": False,
}
```

**Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_scan_engine.py::test_internal_article_uses_internal_directive tests/test_scan_engine.py::test_public_article_uses_public_directive tests/test_scan_engine.py::test_missing_settings_row_uses_empty_directive -v
```
Expected: FAIL — analyzer called without `directive` kwarg

**Step 3: Update scan_engine.py**

In `backend/services/scan_engine.py`, add the `AppSettings` import at the top:

```python
from models import Article, AnalysisResult, ReviewQueue, ScanJob, AppSettings
```

Update `_analyze_and_queue` to accept and pass the directive:

Current signature:
```python
    def _analyze_and_queue(self, article: Article) -> bool:
```

Replace the method with:
```python
    def _analyze_and_queue(self, article: Article, directive: str = "") -> bool:
        # Skip if already pending in queue; return False to indicate no new entry
        existing = (
            self.db.query(ReviewQueue)
            .filter_by(article_id=article.id, status="pending")
            .first()
        )
        if existing:
            return False
        result = self.analyzer.analyze(title=article.title, body=article.body, directive=directive)
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
```

Add a helper method `_load_directive` to `ScanEngine`:

```python
    def _load_directive(self, is_public: bool) -> str:
        row = self.db.query(AppSettings).first()
        if row is None:
            return ""
        return row.public_directive if is_public else row.internal_directive
```

Update both scan methods to load directive and pass it. In `run_heuristic_scan`, change:
```python
                if self.heuristic.needs_review(article_dict):
                    if self._analyze_and_queue(article):
```
to:
```python
                if self.heuristic.needs_review(article_dict):
                    directive = self._load_directive(bool(article.is_public))
                    if self._analyze_and_queue(article, directive=directive):
```

In `run_full_batch_scan`, change:
```python
                if self._analyze_and_queue(article):
```
to:
```python
                directive = self._load_directive(bool(article.is_public))
                if self._analyze_and_queue(article, directive=directive):
```

**Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_scan_engine.py -v
```
Expected: All scan_engine tests PASS (including the 3 new ones)

**Step 5: Run full test suite**

```bash
cd backend && python -m pytest tests/ -v
```
Expected: All prior passing tests still pass + 3 new passing.

**Step 6: Commit**

```bash
git add backend/services/scan_engine.py backend/tests/test_scan_engine.py
git commit -m "feat: load AI directive from DB in ScanEngine, route by article visibility"
```

---

### Task 5: Frontend API module for settings

**Files:**
- Create: `frontend/src/api/settings.ts`

**Step 1: Create the API module**

No failing test needed for a thin API wrapper. Create `frontend/src/api/settings.ts`:

```typescript
// frontend/src/api/settings.ts
import { apiClient } from './client'

export interface AppSettings {
  internal_directive: string
  public_directive: string
}

export async function getSettings(): Promise<AppSettings> {
  return apiClient<AppSettings>('/api/settings')
}

export async function patchSettings(patch: Partial<AppSettings>): Promise<AppSettings> {
  return apiClient<AppSettings>('/api/settings', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
  })
}
```

Check `frontend/src/api/client.ts` first to confirm the `apiClient` function signature — it likely wraps `fetch` and throws on non-2xx. Match that pattern exactly.

**Step 2: Commit**

```bash
git add frontend/src/api/settings.ts
git commit -m "feat: add settings API module (getSettings, patchSettings)"
```

---

### Task 6: Update Settings.tsx with interactive AI Directives section

**Files:**
- Modify: `frontend/src/views/Settings.tsx`

**Step 1: Implement the updated Settings.tsx**

Replace the entire file content with:

```tsx
// frontend/src/views/Settings.tsx
import { useState, useEffect } from 'react'
import { getSettings, patchSettings, type AppSettings } from '../api/settings'

const ENV_VARS = [
  ['ANTHROPIC_API_KEY', 'Anthropic API key for Claude analysis'],
  ['TDX_BASE_URL', 'TeamDynamix instance base URL'],
  ['TDX_APP_ID', 'TDX Knowledge Base application ID'],
  ['TDX_USERNAME', 'TDX username for API authentication'],
  ['TDX_PASSWORD', 'TDX password for API authentication'],
  ['SCAN_CRON', 'Cron expression for heuristic scan schedule (default: 0 2 * * *)'],
  ['HEURISTIC_THRESHOLD', 'Score below which articles are flagged (default: 5.0)'],
  ['CLAUDE_MODEL', 'Claude model to use (default: claude-sonnet-4-6)'],
]

type SaveStatus = 'idle' | 'loading' | 'saving' | 'saved' | 'error'

export default function Settings() {
  const [internal, setInternal] = useState('')
  const [pub, setPub] = useState('')
  const [status, setStatus] = useState<SaveStatus>('loading')
  const [errorMsg, setErrorMsg] = useState('')

  useEffect(() => {
    getSettings()
      .then((data) => {
        setInternal(data.internal_directive)
        setPub(data.public_directive)
        setStatus('idle')
      })
      .catch(() => {
        setStatus('error')
        setErrorMsg('Failed to load settings.')
      })
  }, [])

  async function handleSave() {
    setStatus('saving')
    setErrorMsg('')
    try {
      const updated = await patchSettings({
        internal_directive: internal,
        public_directive: pub,
      })
      setInternal(updated.internal_directive)
      setPub(updated.public_directive)
      setStatus('saved')
      setTimeout(() => setStatus('idle'), 2000)
    } catch {
      setStatus('error')
      setErrorMsg('Failed to save settings.')
    }
  }

  const isBusy = status === 'loading' || status === 'saving'

  return (
    <div>
      <h1 className="mt-0 mb-2 text-2xl font-bold text-slate-800">Settings</h1>

      {/* Env vars reference table — unchanged */}
      <p className="text-slate-500 mb-5">
        All credentials and configuration are managed via the{' '}
        <code className="bg-slate-100 px-1.5 py-0.5 rounded text-sm font-mono">.env</code>{' '}
        file in the project root. Restart the backend after making changes.
      </p>
      <div className="bg-white border border-slate-200 rounded-lg overflow-hidden mb-8">
        <table className="w-full border-collapse">
          <thead>
            <tr className="bg-slate-100">
              <th className="px-4 py-3 text-left font-semibold text-sm text-gray-700">Variable</th>
              <th className="px-4 py-3 text-left font-semibold text-sm text-gray-700">Description</th>
            </tr>
          </thead>
          <tbody>
            {ENV_VARS.map(([key, desc]) => (
              <tr key={key} className="border-t border-slate-200">
                <td className="px-4 py-3 font-mono text-sm font-semibold text-slate-800 whitespace-nowrap">{key}</td>
                <td className="px-4 py-3 text-sm text-slate-500">{desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* AI Directives — interactive */}
      <h2 className="text-lg font-semibold text-slate-800 mb-1">AI Directives</h2>
      <p className="text-slate-500 text-sm mb-5">
        These directives are injected into the Claude analysis prompt as institutional context.
        Changes take effect on the next scan. Use separate directives to tailor tone and detail
        for internal staff vs. public-facing audiences.
      </p>

      {status === 'loading' && (
        <p className="text-slate-400 text-sm">Loading…</p>
      )}

      {status !== 'loading' && (
        <div className="space-y-6">
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-1">
              Internal Articles{' '}
              <span className="font-normal text-slate-400">(non-public)</span>
            </label>
            <textarea
              className="w-full h-52 px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono text-slate-800 resize-y focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={internal}
              onChange={(e) => { setInternal(e.target.value); setStatus('idle') }}
              disabled={isBusy}
              placeholder="Describe the institutional context for internal articles…"
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-1">
              Public Articles
            </label>
            <textarea
              className="w-full h-52 px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono text-slate-800 resize-y focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={pub}
              onChange={(e) => { setPub(e.target.value); setStatus('idle') }}
              disabled={isBusy}
              placeholder="Describe the institutional context for public-facing articles…"
            />
          </div>

          <div className="flex items-center gap-4">
            <button
              onClick={handleSave}
              disabled={isBusy}
              className="px-5 py-2 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {status === 'saving' ? 'Saving…' : 'Save Directives'}
            </button>
            {status === 'saved' && (
              <span className="text-green-600 text-sm font-medium">Saved</span>
            )}
            {status === 'error' && (
              <span className="text-red-600 text-sm">{errorMsg}</span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
```

**Step 2: Check the apiClient signature**

Before running, open `frontend/src/api/client.ts` and verify `apiClient` takes `(path, init?)` and returns a typed promise. If the signature differs, adjust the `settings.ts` calls accordingly.

**Step 3: Start both servers and verify manually**

```bash
# Terminal 1
source backend/.venv/bin/activate && cd backend && uvicorn main:app --reload

# Terminal 2
cd frontend && npm run dev
```

1. Open http://localhost:5173
2. Navigate to Settings
3. Verify both textareas load with pre-populated Cedarville text
4. Edit one textarea, click "Save Directives"
5. Verify "Saved" flash appears
6. Refresh page — edits should persist

**Step 4: Commit**

```bash
git add frontend/src/views/Settings.tsx frontend/src/api/settings.ts
git commit -m "feat: interactive AI directives in Settings screen, saved to DB"
```

---

### Task 7: Final verification

**Step 1: Run full test suite**

```bash
cd backend && python -m pytest tests/ -v
```
Expected: 61/63 passing (all prior + 9 new; same 2 known failures in test_tdx_client.py)

**Step 2: Smoke test the full flow**

With both servers running:
1. Settings → verify textareas show defaults
2. Edit internal directive to add "TEST MARKER internal"
3. Save → "Saved" flash
4. Refresh → edits persist
5. Edit public directive, save
6. (Optional) Trigger a scan and confirm no errors in backend logs

**Step 3: Final commit if anything was missed**

```bash
git add -p  # review any remaining changes
git commit -m "chore: final cleanup for configurable AI directives"
```
