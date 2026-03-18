# backend/tests/test_claude_client.py
import pytest
from unittest.mock import MagicMock, patch
from services.claude_client import ClaudeAnalyzer, AnalysisResult

SAMPLE_INPUT = {
    "score_clarity": 6.0,
    "score_completeness": 5.0,
    "score_findability": 7.0,
    "score_redundancy": 8.0,
    "score_accuracy": 6.0,
    "overall_score": 6.4,
    "issue_summary": "Article is incomplete and lacks clear steps.",
    "defects": ["Missing resolution steps", "Vague title"],
    "proposed_body": "<p>Improved content here.</p>",
    "approval_tier": "confirm",
}


def _make_tool_response(input_dict):
    """Build a mock Claude response that looks like a tool_use block."""
    block = MagicMock()
    block.type = "tool_use"
    block.name = "analyze_article"
    block.input = input_dict
    mock_response = MagicMock()
    mock_response.content = [block]
    return mock_response


def test_analyze_returns_analysis_result():
    analyzer = ClaudeAnalyzer(api_key="fake", model="claude-sonnet-4-6")
    with patch.object(analyzer.client.messages, "create", return_value=_make_tool_response(SAMPLE_INPUT)):
        result = analyzer.analyze(title="Test Article", body="Some content")
    assert isinstance(result, AnalysisResult)
    assert result.score_clarity == 6.0
    assert result.approval_tier == "confirm"
    assert "Missing resolution steps" in result.defects


def test_analyze_assigns_auto_tier():
    analyzer = ClaudeAnalyzer(api_key="fake", model="claude-sonnet-4-6")
    auto_input = {**SAMPLE_INPUT, "approval_tier": "auto"}
    with patch.object(analyzer.client.messages, "create", return_value=_make_tool_response(auto_input)):
        result = analyzer.analyze(title="Good Article", body="Complete content")
    assert result.approval_tier == "auto"


def test_analyze_raises_when_tool_not_called():
    """If Claude doesn't call the tool, _extract_tool_input raises ValueError."""
    analyzer = ClaudeAnalyzer(api_key="fake", model="claude-sonnet-4-6")
    bad_block = MagicMock()
    bad_block.type = "text"
    mock_response = MagicMock()
    mock_response.content = [bad_block]
    with patch.object(analyzer.client.messages, "create", return_value=mock_response):
        with pytest.raises(ValueError, match="did not call analyze_article"):
            analyzer.analyze(title="Test", body="Content")


def test_analyze_tool_passed_to_api():
    """The analyze_article tool definition must be sent with every API call."""
    analyzer = ClaudeAnalyzer(api_key="fake", model="claude-sonnet-4-6")
    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return _make_tool_response(SAMPLE_INPUT)

    with patch.object(analyzer.client.messages, "create", side_effect=fake_create):
        analyzer.analyze(title="Test", body="Content")

    assert "tools" in captured
    assert captured["tools"][0]["name"] == "analyze_article"
    tool_choice = captured.get("tool_choice", {})
    assert tool_choice.get("name") == "analyze_article"


def test_analyze_injects_directive_into_prompt(monkeypatch):
    """The directive text should appear in the prompt sent to Claude."""
    captured = {}

    class FakeMessages:
        def create(self, **kwargs):
            captured["prompt"] = kwargs["messages"][0]["content"]
            return _make_tool_response(SAMPLE_INPUT)

    class FakeClient:
        messages = FakeMessages()

    import anthropic
    monkeypatch.setattr(anthropic, "Anthropic", lambda **kw: FakeClient())

    from services.claude_client import ClaudeAnalyzer
    analyzer = ClaudeAnalyzer(api_key="test")
    analyzer.analyze(title="T", body="B", directive="MY CUSTOM DIRECTIVE")
    assert "MY CUSTOM DIRECTIVE" in captured["prompt"]
