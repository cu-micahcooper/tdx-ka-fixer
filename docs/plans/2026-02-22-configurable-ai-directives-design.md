# Configurable AI Directives — Design

**Date:** 2026-02-22
**Status:** Approved

## Problem

The Claude analysis prompt contains hardcoded Cedarville University institutional context (systems, tone, audience). This can't be changed without editing source code, and there's no way to give Claude different guidance for internal (non-public) vs. public-facing articles.

The Settings screen is also purely static — a read-only reference table with no interactivity.

## Goal

1. Move the hardcoded institutional context out of `claude_client.py` and into a DB-backed setting editable from the UI.
2. Support separate directives for internal (non-public) and public articles.
3. Make the Settings screen interactive for AI directives specifically; env-var table stays read-only.

## Design

### Data Layer

New `AppSettings` model in `models.py` — single row, always exactly one record (id=1):

```python
class AppSettings(Base):
    __tablename__ = "app_settings"
    id = Column(Integer, primary_key=True)  # always 1
    internal_directive = Column(Text, nullable=False, default="")
    public_directive = Column(Text, nullable=False, default="")
```

### API

New `routers/settings.py` mounted at `/api/settings`:

- `GET /api/settings` — returns `{ internal_directive, public_directive }`. If no row exists yet, seeds it with the current hardcoded Cedarville text as defaults and returns that.
- `PATCH /api/settings` — accepts `{ internal_directive?, public_directive? }` (partial), saves to DB, returns updated object.

### Claude Prompt Changes

`ANALYSIS_PROMPT` in `claude_client.py`:
- The `## Institutional Context` block is replaced with a `{directive}` placeholder.
- The `## Critical rewrite rules` block (no placeholders, preserve links, etc.) stays hardcoded — it's universal, not institution-specific.

`ClaudeAnalyzer.analyze()` gets a new `directive: str` parameter injected into the prompt.

### Scan Engine Changes

`ScanEngine._analyze_and_queue(article)` loads `AppSettings` from DB, selects the right directive:

```python
directive = settings.public_directive if article.is_public else settings.internal_directive
result = self.analyzer.analyze(title=article.title, body=article.body, directive=directive)
```

### Frontend

`Settings.tsx` adds a second section — **"AI Directives"** — below the existing env-var table:
- Two labeled textareas: "Internal Articles" and "Public Articles"
- Fetches current values on mount via `GET /api/settings`
- Save button (disabled when clean, shows "Saving…" in flight, "Saved" flash on success)
- Error state if PATCH fails

New `frontend/src/api/settings.ts` with `getSettings()` and `patchSettings()`.

## What Stays the Same

- Env-var table: unchanged, read-only
- Universal rewrite rules in the hardcoded prompt: unchanged
- All other backend services, routers, models: unchanged
- No new UI routes or nav items

## Files Touched

| File | Change |
|------|--------|
| `backend/models.py` | Add `AppSettings` model |
| `backend/routers/settings.py` | New router |
| `backend/main.py` | Mount settings router |
| `backend/services/claude_client.py` | Add `directive` param, replace hardcoded context block |
| `backend/services/scan_engine.py` | Load settings, pass directive to analyze() |
| `frontend/src/api/settings.ts` | New API module |
| `frontend/src/views/Settings.tsx` | Add interactive AI directives section |
