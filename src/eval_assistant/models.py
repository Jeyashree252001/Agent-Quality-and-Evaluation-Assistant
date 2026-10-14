from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TestCategory(str, Enum):
    """The 7 required evaluation categories."""
    __test__ = False
    NORMAL_INPUT = "normal_input"
    INCOMPLETE_INPUT = "incomplete_input"
    AMBIGUOUS_INPUT = "ambiguous_input"
    OUT_OF_SCOPE = "out_of_scope"
    INVALID_INPUT = "invalid_input"
    TOOL_FAILURE = "tool_failure"
    UNSUPPORTED_ASSUMPTION = "unsupported_assumption"


class ExpectedBehavior(BaseModel):
    """Expected output characteristics and constraints for a test case."""
    must_succeed: bool = Field(default=True, description="Whether the agent is expected to process or reject cleanly")
    expected_status: Optional[str] = Field(default=None, description="Expected status (e.g. extracted, clarification_needed, rejected, error_recovered)")
    expected_assignee: Optional[str] = Field(default=None, description="Expected assignee name, if definite")
    forbidden_assignees: List[str] = Field(default_factory=list, description="Assignees that MUST NOT be assigned (hallucination check)")
    forbidden_claims: List[str] = Field(default_factory=list, description="Substrings or facts that must not be claimed as confirmed")
    required_fields: List[str] = Field(default_factory=list, description="Fields required in structured output")
    uncertainty_required: bool = Field(default=False, description="Whether the agent must signal uncertainty/ambiguity")
    min_confidence: Optional[float] = Field(default=None, description="Minimum allowable confidence")
    max_confidence: Optional[float] = Field(default=None, description="Maximum allowable confidence (e.g. For ambiguous inputs)")
    expected_tools: List[str] = Field(default_factory=list, description="Tools expected to be called")
    rejection_expected: bool = Field(default=False, description="Whether the agent must reject the request as out-of-scope or invalid")
    tool_failure_simulated: bool = Field(default=False, description="Whether downstream tool will fail")


class TestCase(BaseModel):
    """Definition of an evaluation test case."""
    __test__ = False
    id: str = Field(description="Unique identifier e.g. TC-01-NORMAL")
    category: TestCategory = Field(description="One of the 7 required test categories")
    title: str = Field(description="Short human-readable title")
    description: str = Field(description="Explanation of the test scenario")
    input_text: str = Field(description="Raw text input presented to the target agent")
    context: Dict[str, Any] = Field(default_factory=dict, description="Optional extra metadata or session state")
    expected: ExpectedBehavior = Field(description="Expected behavior specification")
    rationale: str = Field(description="Why this test is significant and what regression it guards against")
    target_behavior_mode: Optional[str] = Field(
        default="default",
        description="Behavioral mode for the target agent: 'default', 'hallucinating', 'flaky_tool', 'overconfident'"
    )


class ToolCallRecord(BaseModel):
    """Record of an external tool invocation performed by the target agent."""
    tool_name: str
    args: Dict[str, Any] = Field(default_factory=dict)
    status: str = Field(default="success", description="'success' or 'failed'")
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class TargetAgentResponse(BaseModel):
    """Standardized response output produced by the target agent."""
    raw_text: str = Field(description="Natural language summary or reply")
    structured_output: Dict[str, Any] = Field(default_factory=dict, description="Structured extracted payload")
    status: str = Field(description="Status e.g. 'success', 'clarification_needed', 'rejected', 'error_recovered', 'unsupported_request'")
    action_items: List[Dict[str, Any]] = Field(default_factory=list, description="Extracted actionable tasks")
    clarification_questions: List[str] = Field(default_factory=list, description="Questions asked if ambiguous/incomplete")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score reported by agent")
    tool_calls: List[ToolCallRecord] = Field(default_factory=list, description="External tool calls made")
    error: Optional[str] = Field(default=None, description="System/execution error message, if any")
    execution_time_ms: float = Field(default=0.0, description="Latency in milliseconds")


class EvaluatorType(str, Enum):
    """Categorization of evaluator methodology."""
    DETERMINISTIC_SCHEMA = "deterministic_schema"
    DETERMINISTIC_CONTENT = "deterministic_content"
    DETERMINISTIC_TOOL = "deterministic_tool"
    DETERMINISTIC_GROUNDING = "deterministic_grounding"
    DETERMINISTIC_UNCERTAINTY = "deterministic_uncertainty"
    MODEL_JUDGE = "model_judge"


class CheckResult(BaseModel):
    """The outcome of a single evaluation check."""
    check_name: str
    evaluator_type: EvaluatorType
    passed: bool
    score: float = Field(ge=0.0, le=1.0)
    reason: str
    evidence: str = Field(default="", description="Relevant snippet or comparison proving the pass/fail")
    suggested_fix: Optional[str] = Field(default=None, description="Actionable recommendation for agent improvement")
    requires_human_review: bool = Field(default=False, description="Flagged for human triage when confidence is borderline")


class TestCaseEvaluation(BaseModel):
    """The complete aggregated evaluation result for one test case."""
    test_case: TestCase
    agent_response: TargetAgentResponse
    overall_passed: bool
    checks: List[CheckResult] = Field(default_factory=list)
    failure_reasons: List[str] = Field(default_factory=list)
    suggested_improvements: List[str] = Field(default_factory=list)
    requires_human_review: bool = False
    evaluation_time_ms: float = 0.0


class EvaluationSummary(BaseModel):
    """Comprehensive summary report across all executed test cases."""
    timestamp: str
    eval_mode: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    review_needed: int
    pass_rate_percentage: float
    results_by_category: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    evaluations: List[TestCaseEvaluation] = Field(default_factory=list)
