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

## Fresh Install Guide

Use these steps on a new machine or a clean checkout.

### Prerequisites

- Python 3.11+
- Node.js 18+
- npm, which is included with Node.js
- Git
- A Cedarville University TDX account with API access to the Knowledge Base application
- An Anthropic API key with sufficient credits

Verify the local tools:

```bash
python3 --version
node --version
npm --version
git --version
```

The backend uses FastAPI, SQLAlchemy, SQLite, and APScheduler. The frontend uses Vite, React, and Tailwind CSS. SQLite is local to the backend directory and does not require a separate database server.

### 1. Clone the repository

```bash
git clone https://repo.cedarville.edu/micahcooper/tdx-ka-fixer.git
cd tdx-ka-fixer
```

### 2. Create the environment file

Copy the example file from the repository root:

```bash
cp .env.example .env
```

Edit `.env` and fill in real values:

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

Notes:

- `TDX_APP_ID` is the numeric ID of the Knowledge Base application in your TDX instance. For Cedarville it is `2045`. You can find it by listing apps via the TDX API or checking the URL when browsing the KB portal.
- `.env` is read from the repository root when you start the backend from `backend/`.
- Keep `.env` private. It contains credentials that can read and update TDX articles and spend Anthropic API credits.
- `SCAN_CRON=0 2 * * *` runs the scheduled heuristic scan at 2:00 AM in the server's local timezone.

### 3. Set up the backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

For development and tests, also install the test dependencies:

```bash
pip install -r requirements-dev.txt
```

The SQLite database is created automatically as `backend/ka_fixer.db` on first backend startup. Existing local data remains in that file until you delete or replace it.

### 4. Set up the frontend

```bash
cd ../frontend
npm install
```

### 5. Start the backend

Open one terminal:

```bash
cd /path/to/tdx-ka-fixer/backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

Expected result:

- API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

Verify from another terminal:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status":"ok"}
```

If port `8000` is already in use, start the backend on another port:

```bash
uvicorn main:app --reload --port 8001
```

### 6. Start the frontend

Open a second terminal:

```bash
cd /path/to/tdx-ka-fixer/frontend
npm run dev
```

Expected result:

- UI: `http://localhost:5173`
- API requests from the UI proxy to `http://localhost:8000`

If the backend is running on a non-default port, point the Vite proxy at it:

```bash
VITE_API_PROXY_TARGET=http://localhost:8001 npm run dev
```

Verify the frontend is serving:

```bash
curl http://localhost:5173
```

Then open `http://localhost:5173` in a browser.

### 7. Confirm the app can reach the API

With both servers running, verify a proxied API call through Vite:

```bash
curl http://localhost:5173/api/settings
```

That should return the rewrite directives stored in the app settings. If it fails, check that the backend is running and that `VITE_API_PROXY_TARGET` matches the backend URL.

### 8. Run the article scanner

The dashboard has buttons for scans, but you can also trigger them directly.

Heuristic scan, recommended for normal use:

```bash
curl -X POST http://localhost:8000/api/scans/trigger \
  -H 'Content-Type: application/json' \
  -d '{"mode":"heuristic"}'
```

Full batch scan, slower and more expensive:

```bash
curl -X POST http://localhost:8000/api/scans/trigger \
  -H 'Content-Type: application/json' \
  -d '{"mode":"full_batch"}'
```

Check scan history and current status:

```bash
curl http://localhost:8000/api/scans
```

Scans run in a backend background thread. The first phase fetches data from TDX, so progress counters may remain at zero until that fetch completes.

### 9. Shut down

Stop each running terminal with `Ctrl+C`.

If you need to confirm ports are free:

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
lsof -nP -iTCP:5173 -sTCP:LISTEN
```

No output means nothing is listening on that port.

## Running

After the initial setup, the normal daily startup is:

```bash
cd /path/to/tdx-ka-fixer/backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

```bash
cd /path/to/tdx-ka-fixer/frontend
npm run dev
```

The API is available at `http://localhost:8000`. Interactive docs are at `http://localhost:8000/docs`. The UI is available at `http://localhost:5173`.

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

Backend tests:

```bash
cd backend
source .venv/bin/activate
pytest
```

Frontend checks:

```bash
cd frontend
npm run lint
npm run build
```

Run these before pushing changes when possible.

---

## Troubleshooting

### Port 8000 is already in use

Find the process:

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
```

Either stop that process or run this app's backend on another port:

```bash
cd backend
source .venv/bin/activate
uvicorn main:app --reload --port 8001
```

Then start the frontend with:

```bash
cd frontend
VITE_API_PROXY_TARGET=http://localhost:8001 npm run dev
```

### Backend fails during startup

Check these first:

- `.env` exists in the repository root.
- Required values are present: `ANTHROPIC_API_KEY`, `TDX_BASE_URL`, `TDX_APP_ID`, `TDX_USERNAME`, and `TDX_PASSWORD`.
- The virtual environment is active.
- Dependencies were installed with `pip install -r requirements.txt`.

### Scanner fails or times out

Common causes:

- TDX credentials are wrong or do not have Knowledge Base API access.
- TDX rate limits are being hit.
- The Anthropic API key is missing, out of credits, or rate limited.
- A full batch scan is too large for current model or account limits.

Use `GET /api/scans` or the dashboard scan history to inspect the stored error message.

### Frontend loads but API calls fail

Check:

- Backend is running.
- The frontend proxy target matches the backend port.
- If using the default setup, backend is on `http://localhost:8000`.
- If using another backend port, start Vite with `VITE_API_PROXY_TARGET=http://localhost:<port> npm run dev`.

---

## Architecture Notes

- **SQLite with WAL mode** — Enables concurrent reads while a background scan is writing, preventing lock errors in the UI.
- **Per-article commits** — Each article is committed individually during a scan to release write locks and allow the UI to remain responsive.
- **Anchor normalization** — Before pushing to TDX, `<h2 id="anchor">` elements are converted to `<a name="anchor"></a><h2>` because TDX's HTML sanitizer strips `id` attributes from block elements, which would break in-page anchor links.
- **Source scraping** — Articles linking to `cedarville.edu` pages (excluding TDX itself) have those pages scraped at analysis time. The text content is appended to the Claude prompt so rewrites reflect current source material. Up to 3 sources, 3,000 characters each.
- **Rate limit handling** — Both TDX (60 req/min) and Anthropic APIs are handled gracefully with sleep-until-reset logic and exponential backoff on 429 responses.
