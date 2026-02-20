# TDX KA Fixer — Design Document
**Date:** 2026-02-20
**Status:** Approved

---

## Overview

TDX KA Fixer is a locally-run web application that connects to a TeamDynamix (TDX) Knowledge Base via API, uses Claude AI to analyze and improve article quality, and provides a web console for human review and approval before pushing corrections back to the live TDX environment. The system operates within the KCS (Knowledge-Centered Service) framework.

---

## 1. System Architecture

### Stack
- **Backend:** Python 3.12 + FastAPI
- **Frontend:** React + TypeScript + Vite
- **Database:** SQLite via SQLAlchemy
- **Scheduler:** APScheduler (embedded in FastAPI)
- **AI:** Anthropic Claude `claude-sonnet-4-6`
- **Deployment:** Local only (this machine)

### Component Diagram

```
┌─────────────────────────────────────────────────┐
│                  Web Console (React)             │
└────────────────────┬────────────────────────────┘
                     │ REST API
┌────────────────────▼────────────────────────────┐
│                FastAPI Backend                   │
│  ┌─────────────┐  ┌──────────────┐  ┌────────┐ │
│  │ TDX Client  │  │ Scan Engine  │  │ Claude │ │
│  │  (REST API) │  │ (APScheduler)│  │ Client │ │
│  └─────────────┘  └──────────────┘  └────────┘ │
│               ┌──────────┐                      │
│               │  SQLite  │                      │
│               └──────────┘                      │
└─────────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│           TeamDynamix KnowledgeBase API          │
└─────────────────────────────────────────────────┘
```

### Running Locally

```bash
# Backend
cd backend && uvicorn main:app --reload --port 8000

# Frontend
cd frontend && npm run dev   # runs on :5173, proxies API to :8000
```

---

## 2. AI Analysis Pipeline

Articles go through a two-stage pipeline.

### Stage 1 — Heuristic Pre-filter (no API cost)

Scores articles on cheap signals to decide if Claude analysis is warranted:

- Age since last modified
- Article length (too short = incomplete; very long = may need splitting)
- Presence of known defect patterns (`TODO`, `TBD`, broken HTML, placeholder text)
- Low view/reuse count relative to age (KCS signal: findability problem)
- Duplicate title detection across the KB

### Stage 2 — Claude Analysis

Claude performs a structured assessment across five KCS-aligned quality dimensions:

| Dimension | What Claude Evaluates |
|---|---|
| **Clarity** | Readable, well-structured, free of unnecessary jargon |
| **Completeness** | Fully addresses the problem or topic |
| **Findability** | Title and content are searchable and descriptive |
| **Redundancy** | Overlaps significantly with other articles |
| **Accuracy** | Detectable staleness (outdated product names, deprecated steps, dead references) |

Claude returns:
- A quality score per dimension (0–10)
- An overall score
- A summary of issues found
- A list of specific defects
- A fully rewritten version of the article

### Scan Modes

| Mode | Trigger | Behavior |
|---|---|---|
| **Continuous (default)** | Scheduled (configurable interval) | Heuristic pre-filter only; flagged articles enter Claude queue |
| **Full Batch** | Manually triggered from web console | All articles sent through Claude regardless of heuristic score |

### Approval Tiers

| Change Type | Required Approval |
|---|---|
| Formatting, whitespace, typos | Auto-approvable (bulk-approve available in console) |
| Grammar, clarity rewrites | Single reviewer confirm |
| Content additions or restructuring | Single reviewer confirm |
| Major rewrite or significant content change | Explicit approve with diff review |
| Article flagged for archival/deletion | Admin confirmation |

---

## 3. Web Console

### Five Views

**Dashboard**
- KB health summary: total articles, % reviewed, average quality scores by dimension
- Queue stats: pending review, auto-approvable, requires admin
- Scan status: last run, next scheduled run, trigger Full Batch scan
- Recent activity feed (approvals, rejections, articles pushed to TDX)

**Article Browser**
- Browse and search all TDX articles from local cache
- Filter by category, quality score, last modified, approval tier, status
- Manually queue any article for Claude analysis

**Review Queue** *(primary work surface)*
- Article-by-article review with side-by-side or unified diff of original vs. proposed rewrite
- Per-article: Claude issue summary, per-dimension quality scores, approval tier badge
- Actions: **Approve**, **Reject**, **Edit then Approve**, **Skip**, **Flag for Admin**
- Bulk-approve available for auto-approvable tier

**Audit Log**
- Immutable history of every change pushed to TDX
- Revert capability: re-queues article with previous version as the proposed change

**Settings**
- TDX API credentials
- Scan schedule (cron expression)
- Quality score thresholds per approval tier
- Claude model selection

### Review Flow

```
Article flagged → Claude analysis → Approval tier assigned
    → Queue → Reviewer sees diff → Approve / Edit / Reject
        → Approved:  pushed to TDX via API + audit logged
        → Rejected:  dismissed, reason logged
        → Edit:      reviewer modifies proposed text inline, then approves
```

---

## 4. Data Model

Six SQLite tables. Article body content stored as `TEXT`; special characters (quotes, parentheses, HTML) handled safely via SQLAlchemy parameterized queries.

### `articles`
Local cache of TDX KB articles.
```
id, tdx_id, title, body, category_id, category_name,
created_at, modified_at, last_synced_at, view_count,
heuristic_score, status (active/archived)
```

### `analysis_results`
Claude's assessment per article.
```
id, article_id, analyzed_at, model_used,
score_clarity, score_completeness, score_findability,
score_redundancy, score_accuracy, overall_score,
issue_summary, defects_json, proposed_body, approval_tier
```

### `review_queue`
Articles pending human action.
```
id, article_id, analysis_id, queued_at,
status (pending/approved/rejected/skipped),
reviewer_note, reviewed_at
```

### `approved_changes`
Changes approved and ready to push (or already pushed).
```
id, review_queue_id, article_id,
original_body, approved_body, approved_at,
pushed_at, push_status (pending/success/failed), push_error
```

### `audit_log`
Immutable record of every TDX write.
```
id, article_id, tdx_id, action (update/archive),
original_body, new_body, approved_at, pushed_at, reverted_at
```

### `scan_jobs`
History of scan runs.
```
id, started_at, completed_at, mode (heuristic/full_batch),
articles_scanned, articles_flagged, status, error
```

---

## 5. TDX API Integration

### Endpoints

| Operation | Endpoint |
|---|---|
| Get auth token | `POST /api/auth/loginadmin` |
| List KB articles | `GET /api/{appId}/knowledge-base/articles/` |
| Get article detail | `GET /api/{appId}/knowledge-base/articles/{id}` |
| Update article | `POST /api/{appId}/knowledge-base/articles/{id}` |
| List categories | `GET /api/{appId}/knowledge-base/categories` |

Authentication uses a Bearer token obtained at startup and refreshed on expiry.

### Project Structure

```
tdx-ka-fixer/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Settings loaded from .env
│   ├── database.py          # SQLAlchemy setup
│   ├── models/              # SQLAlchemy table models
│   ├── routers/             # FastAPI route handlers
│   │   ├── articles.py
│   │   ├── queue.py
│   │   ├── scans.py
│   │   └── audit.py
│   ├── services/
│   │   ├── tdx_client.py    # TDX API wrapper
│   │   ├── claude_client.py # Anthropic API wrapper
│   │   ├── scanner.py       # Heuristic + batch scan logic
│   │   └── approval.py      # Tier assignment + push logic
│   └── scheduler.py         # APScheduler setup
├── frontend/
│   ├── src/
│   │   ├── views/           # Dashboard, Browser, Queue, Audit, Settings
│   │   ├── components/      # DiffViewer, ArticleCard, QueueItem, etc.
│   │   └── api/             # Typed fetch wrappers for backend
│   └── vite.config.ts
├── .env                     # API keys and credentials (git-ignored)
├── .env.example             # Template for credentials
└── ka_fixer.db              # SQLite database (git-ignored)
```

---

## 6. Credentials & Security

- All credentials stored in `.env` (git-ignored)
- `.env.example` committed as a template:
  ```
  ANTHROPIC_API_KEY=
  TDX_BASE_URL=
  TDX_APP_ID=
  TDX_USERNAME=
  TDX_PASSWORD=
  ```
- TDX auth token held in memory, never persisted to disk
- SQLAlchemy parameterized queries throughout — no raw SQL string interpolation
