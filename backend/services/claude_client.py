# backend/services/claude_client.py
import json
from dataclasses import dataclass, field
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
{body}"""


def _extract_json(text: str) -> dict:
    """Extract JSON from Claude response, handling markdown code fences."""
    text = text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove first line (```json or ```) and last line (```)
        text = "\n".join(lines[1:-1]).strip()
    return json.loads(text)


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

    def analyze(self, title: str, body: str) -> AnalysisResult:
        prompt = ANALYSIS_PROMPT.format(title=title, body=body)
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
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
