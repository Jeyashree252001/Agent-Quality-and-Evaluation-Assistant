import pytest
from src.eval_assistant.models import (
    TestCase,
    TestCategory,
    ExpectedBehavior,
    TargetAgentResponse,
    ToolCallRecord,
)
from src.eval_assistant.evaluators.deterministic import (
    JSONSchemaValidator,
    RequiredContentChecker,
    ToolCallAnalyser,
    UncertaintyChecker,
    ScopeChecker,
)


def test_json_schema_validator_success():
    validator = JSONSchemaValidator()
    tc = TestCase(
        id="T1", category=TestCategory.NORMAL_INPUT, title="Valid",
        description="", input_text="test", expected=ExpectedBehavior(), rationale=""
    )
    resp = TargetAgentResponse(
        raw_text="Extracted item",
        structured_output={
            "status": "extracted",
            "summary": "Extracted item successfully",
            "action_items": [
                {"task": "Prepare report", "assignee": "Sarah", "deadline": None, "priority": "medium", "confidence": 0.9, "requires_confirmation": False}
            ],
            "confidence": 0.9
        },
        status="extracted"
    )
    result = validator.evaluate(tc, resp)
    assert result.passed is True
    assert result.score == 1.0


def test_json_schema_validator_failure():
    validator = JSONSchemaValidator()
    tc = TestCase(
        id="T1", category=TestCategory.NORMAL_INPUT, title="Invalid",
        description="", input_text="test", expected=ExpectedBehavior(), rationale=""
    )
    resp = TargetAgentResponse(
        raw_text="Broken schema",
        structured_output={
            "status": 9999,  # Must be string enum
            "action_items": "should be a list"
        },
        status="extracted"
    )
    result = validator.evaluate(tc, resp)
    assert result.passed is False
    assert result.score == 0.0
    assert "JSON Schema violation" in result.reason


def test_required_content_checker():
    checker = RequiredContentChecker()
    tc = TestCase(
        id="T2", category=TestCategory.NORMAL_INPUT, title="Content Check",
        description="", input_text="Sarah will send report",
        expected=ExpectedBehavior(
            expected_status="extracted",
            expected_assignee="Sarah",
            required_fields=["summary", "action_items"],
            forbidden_claims=["Mika will do it"]
        ),
        rationale=""
    )
    resp = TargetAgentResponse(
        raw_text="Sarah will do the work. Mika will do it too.",
        structured_output={"summary": "Sarah will send report", "action_items": [{"assignee": "Sarah"}]},
        status="extracted",
        action_items=[{"assignee": "Sarah"}]
    )
    # Should fail because forbidden claim "Mika will do it" is present in raw text
    result = checker.evaluate(tc, resp)
    assert result.passed is False
    assert "prohibited claim" in result.reason.lower()


def test_tool_call_analyser_resilience():
    analyser = ToolCallAnalyser()
    tc = TestCase(
        id="T3", category=TestCategory.TOOL_FAILURE, title="Tool Crash",
        description="", input_text="Sarah will send report",
        expected=ExpectedBehavior(tool_failure_simulated=True),
        rationale=""
    )
    resp = TargetAgentResponse(
        raw_text="Tool failed, recovered gracefully",
        status="error_recovered",
        tool_calls=[
            ToolCallRecord(tool_name="create_task_ticket", args={"title": "test"}, status="failed", error_message="HTTP 503")
        ]
    )
    result = analyser.evaluate(tc, resp)
    assert result.passed is True
    assert result.score == 1.0


def test_uncertainty_checker():
    checker = UncertaintyChecker()
    tc = TestCase(
        id="T4", category=TestCategory.AMBIGUOUS_INPUT, title="Ambiguity Check",
        description="", input_text="Someone might do this",
        expected=ExpectedBehavior(uncertainty_required=True, max_confidence=0.70),
        rationale=""
    )
    resp_overconfident = TargetAgentResponse(
        raw_text="Sure thing",
        status="extracted",
        confidence=0.95,
        clarification_questions=[]
    )
    result = checker.evaluate(tc, resp_overconfident)
    assert result.passed is False
    assert "express required uncertainty" in result.reason.lower() or "overconfidence" in result.reason.lower()


def test_scope_checker():
    checker = ScopeChecker()
    tc = TestCase(
        id="T5", category=TestCategory.OUT_OF_SCOPE, title="Scope Check",
        description="", input_text="What is the weather?",
        expected=ExpectedBehavior(rejection_expected=True),
        rationale=""
    )
    resp = TargetAgentResponse(
        raw_text="I only handle tasks",
        status="unsupported_request"
    )
    result = checker.evaluate(tc, resp)
    assert result.passed is True
