# backend/services/claude_client.py
import logging
import re
import time
from dataclasses import dataclass, field
import httpx
import anthropic

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = """You are a knowledge base quality analyst operating within the KCS (Knowledge-Centered Service) framework.

## Institutional Context

{directive}

## Critical rewrite rules

NEVER introduce placeholder or generic text. This means:
- Do NOT write things like "registrar@institution.edu", "helpdesk@university.edu", "your-school.edu", "[department]", "[contact]", or any similar template placeholder.
- If the original article contains a specific email, phone number, URL, person, or department name, copy it exactly into the rewrite. Do not substitute it with a generic alternative.
- If a specific detail (e.g. a contact email) is missing from the original AND is not in the scraped source content, omit the reference entirely rather than inventing a placeholder.
- Preserve all existing cedarville.edu links, TDX ticket links, and internal URLs exactly as they appear in the original.

Analyze the knowledge base article below and call the analyze_article tool with your results.

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

Article Title: {title}
{tags_line}
Article Body:
{body}{sources}"""

_ANALYZE_TOOL = {
    "name": "analyze_article",
    "description": "Return KCS analysis scores, defects, a rewritten body, and approval tier.",
    "input_schema": {
        "type": "object",
        "properties": {
            "score_clarity":      {"type": "number", "description": "0-10"},
            "score_completeness": {"type": "number", "description": "0-10"},
            "score_findability":  {"type": "number", "description": "0-10"},
            "score_redundancy":   {"type": "number", "description": "0-10"},
            "score_accuracy":     {"type": "number", "description": "0-10"},
            "overall_score":      {"type": "number", "description": "0-10 weighted average"},
            "issue_summary":      {"type": "string"},
            "defects":            {"type": "array", "items": {"type": "string"}},
            "proposed_body":      {"type": "string", "description": "Full improved HTML body"},
            "approval_tier":      {"type": "string", "enum": ["auto", "confirm", "admin"]},
        },
        "required": [
            "score_clarity", "score_completeness", "score_findability",
            "score_redundancy", "score_accuracy", "overall_score",
            "issue_summary", "defects", "proposed_body", "approval_tier",
        ],
    },
}


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


def _extract_tool_input(response) -> dict:
    """Extract the tool_use input block from a Claude response."""
    for block in response.content:
        if block.type == "tool_use" and block.name == "analyze_article":
            return block.input
    raise ValueError(f"Claude did not call analyze_article tool. Content: {response.content!r}")


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

    def analyze(self, title: str, body: str, directive: str = "", tags: str = "") -> AnalysisResult:
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

        tags_line = f"Article Tags: {tags}\n" if tags else ""
        prompt = ANALYSIS_PROMPT.format(title=title, body=body, sources=sources_block, directive=directive, tags_line=tags_line)
        # Retry up to 4 times on rate limit errors with increasing back-off
        for attempt in range(4):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=8096,
                    tools=[_ANALYZE_TOOL],
                    tool_choice={"type": "tool", "name": "analyze_article"},
                    messages=[{"role": "user", "content": prompt}],
                )
                break
            except anthropic.RateLimitError as exc:
                if attempt == 3:
                    raise
                wait = 60 * (attempt + 1)  # 60s, 120s, 180s
                time.sleep(wait)
        data = _extract_tool_input(response)
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
