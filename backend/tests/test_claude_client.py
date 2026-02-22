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

def test_analyze_assigns_auto_tier():
    analyzer = ClaudeAnalyzer(api_key="fake", model="claude-sonnet-4-6")
    auto_response = SAMPLE_RESPONSE.replace('"confirm"', '"auto"')
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=auto_response)]
    with patch.object(analyzer.client.messages, "create", return_value=mock_response):
        result = analyzer.analyze(title="Good Article", body="Complete content")
    assert result.approval_tier == "auto"

def test_analyze_raises_on_invalid_json():
    analyzer = ClaudeAnalyzer(api_key="fake", model="claude-sonnet-4-6")
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="not valid json")]
    with patch.object(analyzer.client.messages, "create", return_value=mock_response):
        with pytest.raises(Exception):
            analyzer.analyze(title="Test", body="Content")

def test_analyze_handles_markdown_code_fences():
    analyzer = ClaudeAnalyzer(api_key="fake", model="claude-sonnet-4-6")
    fenced_response = f"```json\n{SAMPLE_RESPONSE}\n```"
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=fenced_response)]
    with patch.object(analyzer.client.messages, "create", return_value=mock_response):
        result = analyzer.analyze(title="Test", body="Content")
    assert result.score_clarity == 6.0

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
