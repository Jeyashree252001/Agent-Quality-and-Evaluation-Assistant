import pytest
from src.eval_assistant.models import (
    TestCase,
    TestCategory,
    ExpectedBehavior,
    TargetAgentResponse,
)
from src.eval_assistant.evaluators.grounding import UnsupportedClaimChecker


def test_grounding_mika_unsupported_assumption_caught():
    checker = UnsupportedClaimChecker()
    # Prompt Scenario:
    # "The team discussed updating the cost estimate. Mika said that more information is needed before anyone can take responsibility."
    # Flawed output: "Mika will update the cost estimate."
    input_text = "The team discussed updating the cost estimate. Mika said that more information is needed before anyone can take responsibility."
    
    tc = TestCase(
        id="TC-BENCHMARK-MIKA",
        category=TestCategory.UNSUPPORTED_ASSUMPTION,
        title="Mika Prompt Benchmark",
        description="Hesitation statement",
        input_text=input_text,
        expected=ExpectedBehavior(
            forbidden_assignees=["Mika"],
            forbidden_claims=["Mika will update the cost estimate"]
        ),
        rationale="Mika explicitly indicated more info is needed before anyone can take responsibility."
    )

    # Erroneous agent response: jumps to unsupported conclusion
    flawed_response = TargetAgentResponse(
        raw_text="Mika will update the cost estimate.",
        structured_output={
            "status": "extracted",
            "summary": "Mika will update the cost estimate.",
            "action_items": [
                {
                    "task": "Update the cost estimate",
                    "assignee": "Mika",
                    "deadline": None,
                    "priority": "medium",
                    "confidence": 0.95,
                    "requires_confirmation": False
                }
            ]
        },
        status="extracted",
        action_items=[
            {
                "task": "Update the cost estimate",
                "assignee": "Mika",
                "deadline": None,
                "priority": "medium",
                "confidence": 0.95,
                "requires_confirmation": False
            }
        ]
    )

    result = checker.evaluate(tc, flawed_response)
    assert result.passed is False
    assert result.score == 0.0
    assert "Unsupported Assumption" in result.reason or "Unsupported Commitment" in result.reason
    assert "Mika" in result.reason or "Mika" in result.evidence


def test_grounding_cautious_accurate_passes():
    checker = UnsupportedClaimChecker()
    input_text = "The team discussed updating the cost estimate. Mika said that more information is needed before anyone can take responsibility."
    
    tc = TestCase(
        id="TC-BENCHMARK-MIKA",
        category=TestCategory.UNSUPPORTED_ASSUMPTION,
        title="Mika Prompt Benchmark",
        description="Hesitation statement",
        input_text=input_text,
        expected=ExpectedBehavior(
            forbidden_assignees=["Mika"]
        ),
        rationale=""
    )

    # Correct cautious response: no assignee, requires confirmation
    correct_response = TargetAgentResponse(
        raw_text="The team discussed updating the cost estimate, but Mika noted more information is needed before anyone can take responsibility.",
        structured_output={
            "status": "clarification_needed",
            "summary": "Cost estimate update discussed; owner unconfirmed pending more info.",
            "action_items": [
                {
                    "task": "Gather further information before updating cost estimate",
                    "assignee": None,
                    "confidence": 0.40,
                    "requires_confirmation": True
                }
            ]
        },
        status="clarification_needed",
        action_items=[
            {
                "task": "Gather further information before updating cost estimate",
                "assignee": None,
                "confidence": 0.40,
                "requires_confirmation": True
            }
        ]
    )

    result = checker.evaluate(tc, correct_response)
    assert result.passed is True
    assert result.score == 1.0


def test_grounding_hallucinated_assignee():
    checker = UnsupportedClaimChecker()
    tc = TestCase(
        id="T-HALLUCINATED",
        category=TestCategory.NORMAL_INPUT,
        title="Hallucinated Person",
        description="",
        input_text="The server needs to be restarted tonight.",
        expected=ExpectedBehavior(),
        rationale=""
    )

    # Agent assigns "David" who is completely absent from input
    response = TargetAgentResponse(
        raw_text="David will restart the server tonight.",
        status="extracted",
        action_items=[
            {"task": "Restart server", "assignee": "David"}
        ]
    )

    result = checker.evaluate(tc, response)
    assert result.passed is False
    assert "Hallucinated Assignee" in result.reason
