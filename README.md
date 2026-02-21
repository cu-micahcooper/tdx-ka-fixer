# TDX KA Tuna

An internal tool for Cedarville University IT that automatically audits, rewrites, and pushes improvements to knowledge base articles in TeamDynamix (TDX). It uses Claude (Anthropic) to score articles across five quality dimensions, generate improved rewrites grounded in live source content, and surface the results in a review queue for staff approval before any change is pushed to TDX.

---

## How It Works

1. **Scan** — The backend fetches all KB articles from TDX, scores each one heuristically (staleness, length, keyword density), and flags low-scoring articles for Claude analysis.
2. **Analyze** — Claude evaluates each flagged article across five dimensions (clarity, completeness, findability, redundancy, accuracy), identifies specific defects, and proposes a full rewrite. If the article links to any `cedarville.edu` source pages, those are scraped and included as context so the rewrite reflects current information.
3. **Review** — A staff member reviews a side-by-side diff of the current vs. proposed body in the web UI, then approves, rejects, or skips each item.
4. **Push** — Approved articles are pushed back to TDX via the API. Changes are logged in the audit trail.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, SQLAlchemy, SQLite |
| AI | Anthropic Claude (`claude-sonnet-4-6`) |
| TDX Integration | TeamDynamix REST API |
| Frontend | React 19, Vite, Tailwind CSS v4, TanStack Query |
| Scheduler | APScheduler (nightly heuristic scan) |

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- A Cedarville University TDX account with API access to the Knowledge Base application
- An Anthropic API key with sufficient credits

---

## Setup

### 1. Clone the repo

```bash
git clone https://repo.cedarville.edu/micahcooper/tdx-ka-fixer.git
cd tdx-ka-fixer
```

### 2. Configure environment variables

Copy the example and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```env
ANTHROPIC_API_KEY=sk-ant-api03-...

# TeamDynamix
TDX_BASE_URL=https://cedarville.teamdynamix.com/TDWebApi
TDX_APP_ID=2045
TDX_USERNAME=your-tdx-username@cedarville.edu
TDX_PASSWORD=your-tdx-password

# Optional overrides (defaults shown)
SCAN_CRON=0 2 * * *       # nightly at 2 AM
HEURISTIC_THRESHOLD=5.0   # articles scoring below this are flagged for Claude
CLAUDE_MODEL=claude-sonnet-4-6
```

> `TDX_APP_ID` is the numeric ID of the Knowledge Base application in your TDX instance. For Cedarville it is `2045`. You can find it by listing apps via the TDX API or checking the URL when browsing the KB portal.

### 3. Set up the backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

The SQLite database (`ka_fixer.db`) is created automatically on first run via SQLAlchemy.

### 4. Set up the frontend

```bash
cd frontend
npm install
```

---

## Running

### Backend

```bash
cd backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

The API is available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm run dev
```

The UI is available at `http://localhost:5173`. API requests are proxied to `http://localhost:8000`.

---

## Usage

### Dashboard

The dashboard shows pending review count, approved-but-not-pushed count, and a summary of the most recent scan. Use the **Trigger Scan** buttons here to kick off a scan on demand:

- **Heuristic Scan** — Scores all articles and sends only low-scoring ones to Claude. Fast and cheap; good for daily use.
- **Full Batch Scan** — Sends every article to Claude regardless of heuristic score. Use sparingly (slow, consumes API credits).

Scans run in the background — the UI won't freeze. Check back or refresh after a few minutes.

### Review Queue

Each pending item shows:
- Article title and a link to view it live in TDX
- Quality scores across five dimensions (red = below 6, green = 6+)
- A summary of identified issues and a defect list
- A side-by-side diff of the current body vs. Claude's proposed rewrite

**Approve** — Records the approval and immediately pushes the proposed body to TDX.
**Reject** — Dismisses the item with an optional note; the article is not changed.
**Skip** — Defers the item without a decision (useful if you want to return to it later).

### Article Browser

Browse all synced articles with filters for status (active/archived), category, and heuristic score range. Uses the locally cached copy of article data — run a scan first to populate it.

### Audit Log

Shows all approved changes and their push status (pending / success / failed). If a push failed, the error message is displayed inline and a **Retry** button is available. **Push All Unpushed** retries every pending or failed change at once.

---

## Running Tests

```bash
cd backend
source .venv/bin/activate
pytest
```

---

## Architecture Notes

- **SQLite with WAL mode** — Enables concurrent reads while a background scan is writing, preventing lock errors in the UI.
- **Per-article commits** — Each article is committed individually during a scan to release write locks and allow the UI to remain responsive.
- **Anchor normalization** — Before pushing to TDX, `<h2 id="anchor">` elements are converted to `<a name="anchor"></a><h2>` because TDX's HTML sanitizer strips `id` attributes from block elements, which would break in-page anchor links.
- **Source scraping** — Articles linking to `cedarville.edu` pages (excluding TDX itself) have those pages scraped at analysis time. The text content is appended to the Claude prompt so rewrites reflect current source material. Up to 3 sources, 3,000 characters each.
- **Rate limit handling** — Both TDX (60 req/min) and Anthropic APIs are handled gracefully with sleep-until-reset logic and exponential backoff on 429 responses.
