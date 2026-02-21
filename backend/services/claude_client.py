# backend/services/claude_client.py
import json
import logging
import re
import time
from dataclasses import dataclass, field
import httpx
import anthropic

logger = logging.getLogger(__name__)

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

Analyze the following knowledge base article and return a JSON object with this exact structure:
{{
  "score_clarity": <0-10 float>,
  "score_completeness": <0-10 float>,
  "score_findability": <0-10 float>,
  "score_redundancy": <0-10 float>,
  "score_accuracy": <0-10 float>,
  "overall_score": <0-10 float, weighted average>,
  "issue_summary": "<1-2 sentence summary of main issues>",
  "defects": ["<specific defect 1>", "<specific defect 2>"],
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
{body}{sources}"""


# ---------------------------------------------------------------------------
# Source scraping helpers
# ---------------------------------------------------------------------------

# Match href values pointing to cedarville.edu (any subdomain)
_CEDARVILLE_HREF_RE = re.compile(
    r'href=["\']?(https?://(?:[a-zA-Z0-9-]+\.)*cedarville\.edu[^"\'>\s]*)',
    re.IGNORECASE,
)
_MAX_SOURCE_CHARS = 3_000   # chars kept per scraped page
_MAX_SOURCES = 3            # max pages to scrape per article


def _extract_source_urls(html_body: str) -> list[str]:
    """Return unique cedarville.edu URLs found in article HTML, excluding TDX itself."""
    seen: set[str] = set()
    urls: list[str] = []
    for m in _CEDARVILLE_HREF_RE.finditer(html_body):
        url = m.group(1).rstrip(".,;)")
        if "teamdynamix.com" not in url and url not in seen:
            seen.add(url)
            urls.append(url)
    return urls[:_MAX_SOURCES]


def _html_to_text(html: str) -> str:
    """Strip HTML tags and normalize whitespace to plain text."""
    # Remove script/style blocks entirely
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    # Replace tags with a space
    text = re.sub(r"<[^>]+>", " ", text)
    # Decode common entities
    for entity, char in [("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                          ("&nbsp;", " "), ("&#39;", "'"), ("&quot;", '"')]:
        text = text.replace(entity, char)
    return re.sub(r"\s+", " ", text).strip()


def _scrape_url(url: str) -> str | None:
    """Fetch a URL and return its plain-text content (up to _MAX_SOURCE_CHARS), or None."""
    try:
        with httpx.Client(timeout=httpx.Timeout(10.0), follow_redirects=True) as http:
            resp = http.get(url, headers={"User-Agent": "TDX-KA-Fixer/1.0"})
        if resp.status_code != 200:
            logger.warning("Scrape %s returned HTTP %s", url, resp.status_code)
            return None
        if "html" not in resp.headers.get("content-type", ""):
            return None
        return _html_to_text(resp.text)[:_MAX_SOURCE_CHARS]
    except Exception as exc:
        logger.warning("Failed to scrape %s: %s", url, exc)
        return None


def _extract_json(text: str) -> dict:
    """Extract JSON from Claude response, handling markdown fences and common quirks."""
    text = text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]).strip()
    # Strip trailing commas before } or ] (common LLM output issue, handles nested)
    text = re.sub(r",(\s*[}\]])", r"\1", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.error("Claude JSON parse failed. Raw response:\n%s", text[:2000])
        raise


@dataclass
class AnalysisResult:
    score_clarity: float
    score_completeness: float
    score_findability: float
    score_redundancy: float
    score_accuracy: float
    overall_score: float
    issue_summary: str
    proposed_body: str
    approval_tier: str
    defects: list[str] = field(default_factory=list)


class ClaudeAnalyzer:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    # ~25k chars ≈ 6k tokens; keeps total prompt well within 10k token/min limit
    _MAX_BODY_CHARS = 25_000

    def analyze(self, title: str, body: str) -> AnalysisResult:
        if len(body) > self._MAX_BODY_CHARS:
            body = body[:self._MAX_BODY_CHARS] + "\n\n[TRUNCATED — article exceeds analysis limit]"

        # Scrape any cedarville.edu sources linked in the article body
        source_urls = _extract_source_urls(body)
        scraped: list[str] = []
        for url in source_urls:
            content = _scrape_url(url)
            if content:
                logger.info("Scraped source for '%s': %s (%d chars)", title, url, len(content))
                scraped.append(f"URL: {url}\n{content}")
        if scraped:
            sources_block = (
                "\n\n## Referenced Sources (scraped — use this content when rewriting)\n\n"
                + "\n\n---\n\n".join(scraped)
            )
        else:
            sources_block = ""

        prompt = ANALYSIS_PROMPT.format(title=title, body=body, sources=sources_block)
        # Retry up to 4 times on rate limit errors with increasing back-off
        for attempt in range(4):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=8096,
                    messages=[{"role": "user", "content": prompt}],
                )
                break
            except anthropic.RateLimitError as exc:
                if attempt == 3:
                    raise
                wait = 60 * (attempt + 1)  # 60s, 120s, 180s
                time.sleep(wait)
        raw = response.content[0].text
        data = _extract_json(raw)
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
