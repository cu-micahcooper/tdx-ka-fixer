# TDX KA Tuna — Build Log
## Questions, Answers, and Directives

This document records the design decisions, Q&A, and directives given during the construction of TDX KA Tuna.

---

## Session 1 — 2026-02-20: Original Project Design

### Initial Directive

> "Build an internal tool that scans our TDX knowledge base for stale and low-quality articles, uses Claude AI to score them and propose rewrites, and lets staff review and approve changes before pushing them back to TDX."

---

### Brainstorm Q&A

**Q: What is the deployment target — local machine, shared server, cloud?**
A: Local only. Single-user tool running on one machine.

**Q: Should this be a web UI or a CLI/script?**
A: Web UI — a React frontend with a FastAPI backend.

**Q: What's the primary goal — catching stale articles, improving clarity, or both?**
A: Both. Stale detection plus full quality improvement using the KCS (Knowledge-Centered Service) framework.

**Q: Should every article go through Claude, or should there be a cheaper pre-filter?**
A: Pre-filter with heuristics first (age, length, known defect patterns), then send flagged articles to Claude. Keeps API costs down.

**Q: What quality dimensions should Claude evaluate?**
A: Five KCS-aligned dimensions — clarity, completeness, findability, redundancy, and accuracy.

**Q: Should all approved changes auto-push, or require human review?**
A: Tiered approval — minor formatting fixes can be bulk-approved, content changes require single reviewer confirmation, major rewrites require explicit diff review.

**Q: Should the tool be able to archive articles, or only update them?**
A: Flag for archival only — no direct deletion. Admin confirms.

**Q: What database?**
A: SQLite — it's a local single-user tool. No need for Postgres.

**Q: Multi-user auth or not?**
A: No auth. Single-user local tool, YAGNI.

---

### Institutional Context Directives

These directives were given to shape Claude's analysis and rewrites:

> "This knowledge base belongs to **Cedarville University** — a private Christian liberal arts university in Cedarville, Ohio. The articles support students, faculty, and staff seeking IT help."

> "Key systems in use: Microsoft 365 (Outlook, Teams, OneDrive, SharePoint), Banner (ERP/student information), Blackboard/Canvas (LMS), Duo (MFA), GlobalProtect VPN, CU-managed Windows and Mac devices."

> "Write in plain, friendly language appropriate for a university help desk. Avoid jargon; define acronyms on first use."

> "Links to cedarville.edu resources should be preserved and treated as authoritative."

> "**NEVER introduce placeholder or generic text** — no `registrar@institution.edu`, `[department]`, `your-school.edu`, or similar. If a specific detail is missing from the original and not in scraped source content, omit it entirely rather than inventing a placeholder."

> "Preserve all existing cedarville.edu links, TDX ticket links, and internal URLs exactly as they appear in the original."

---

## Session 1 — 2026-02-20: Build Directives (Chronological)

These directives were given during implementation, inferred from commit history:

- Fix TDX auth — switch from BEID/WebServicesKey to username/password (`POST /api/auth/login`)
- Fix TDX token parsing, app ID, and add body truncation for Claude
- Use `datetime.now(timezone.utc)` everywhere — drop `utcnow()` deprecation warnings
- Fix push endpoint, TDX 401 retry, flagged count
- Add source scraping — scrape linked cedarville.edu URLs and feed content into Claude prompt for accuracy
- Add Tailwind CSS to the frontend
- Anchor normalization on article links
- Fix category iteration to capture all articles (not just top-level categories)
- Add rate limit handling — `_REQUEST_INTERVAL = 5.0s` between TDX requests
- Make scan trigger async
- **"Forbid placeholder text in Claude rewrites"** — add explicit prompt rules, add `f00b9e4` fix
- Add rich text editor (Tiptap) for editing proposed changes before approval
- Add raw HTML view for article bodies
- Add link editing in the rich text editor
- Add audit log entries with direct TDX article links
- Add article detail view with score breakdown and diff
- Add article status/visibility filtering to Article Browser
- Add dashboard stats (article counts by category, visibility, TDX status)
- Add logo (fish with glasses)
- Ensure all datetime serialization appends "Z" suffix to prevent JS timezone misinterpretation
- **"Rename the product to TDX KA Tuna"**

---

## Session 2 — 2026-02-22: Configurable AI Directives

### Initial Directive

> "Update the settings screen to be interactive and save settings. Move the claude directives I gave you about Cedarville University to a setting that can be configured with AI directives to shape evaluation and improvement of all knowledge articles such as institutional perogatives. Allow for separate directives for internal (non-public) vs external (public) articles."

---

### Brainstorm Q&A

**Q: Beyond AI directives, should the Settings screen also let you interactively edit operational settings like the scan threshold (`HEURISTIC_THRESHOLD`), Claude model, or scan schedule? Or should those stay env-file-only, and the main interactive addition is the AI directives?**

A: "Main interactive is AI direction."

---

**Approach options presented:**

- **A — Single-row `app_settings` table (recommended):** One DB model, typed `internal_directive` and `public_directive` columns. GET seeds defaults, PATCH saves. Simplest design that fits perfectly.
- **B — Generic key-value store:** `Setting(key, value)` table. More complex, no type safety, YAGNI.
- **C — File-based:** Write directives to disk. Breaks the pattern, harder to serve via API.

**Q: Which approach?**
A: "A"

---

**Design Section 1 (Data layer & API) presented — approved?**
A: "Yes"

**Design Section 2 (Frontend UI) presented — approved?**
A: "Y"

---

### Post-Implementation Directives

> "figure out failing tests"
— Two pre-existing failures in `test_tdx_client.py` were fixed:
  - `test_update_article`: test mocked POST but code uses GET then PUT; fixed both mocks
  - `test_401_triggers_reauthentication_and_retry`: side_effect list exhausted (only 2 entries for 11 total search calls); fixed by adding 10 more empty responses + patching `time.sleep`

> "push it"
— Pushed to `git@repo.cedarville.edu:micahcooper/tdx-ka-fixer.git`

---

## Recurring Preferences Expressed

| Preference | Source |
|---|---|
| YAGNI aggressively — no features for hypothetical future needs | Multiple sessions |
| Single-user local tool — no cloud infra, no auth | Session 1 design |
| No auto-commits — push only on explicit request | Ongoing |
| SSH remote: `git@repo.cedarville.edu` | Setup |
| Never fabricate institutional details in rewrites | Institutional context directive |
| All UTC datetimes serialized with "Z" suffix | Build directive |
