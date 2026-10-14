import jsonschema
from typing import Any, Dict, List, Optional
from ..models import (
    TestCase,
    TargetAgentResponse,
    CheckResult,
    EvaluatorType,
    TestCategory,
)
from ..target_agent.schemas import ACTION_AGENT_JSON_SCHEMA
from .base import BaseEvaluator


class JSONSchemaValidator(BaseEvaluator):
    """
    Deterministic validator verifying agent output adheres to strict JSON Schema.
    Checks data types, mandatory keys, and value bounds.
    """

    @property
    def name(self) -> str:
        return "json_schema_validation"

    def evaluate(self, test_case: TestCase, response: TargetAgentResponse) -> CheckResult:
        structured = response.structured_output
        if not structured or not isinstance(structured, dict):
            return CheckResult(
                check_name=self.name,
                evaluator_type=EvaluatorType.DETERMINISTIC_SCHEMA,
                passed=False,
                score=0.0,
                reason="Target agent output is not a valid JSON dictionary.",
                evidence=f"Received: {repr(structured)}",
                suggested_fix="Ensure target agent always returns a well-formed JSON object."
            )

        try:
            jsonschema.validate(instance=structured, schema=ACTION_AGENT_JSON_SCHEMA)
            return CheckResult(
                check_name=self.name,
                evaluator_type=EvaluatorType.DETERMINISTIC_SCHEMA,
                passed=True,
                score=1.0,
                reason="Structured output strictly complies with JSON Schema specification.",
                evidence=f"Validated keys: {list(structured.keys())}"
            )
        except jsonschema.ValidationError as err:
            return CheckResult(
                check_name=self.name,
                evaluator_type=EvaluatorType.DETERMINISTIC_SCHEMA,
                passed=False,
                score=0.0,
                reason=f"JSON Schema violation: {err.message} at path: '{list(err.absolute_path)}'",
                evidence=f"Invalid sub-element: {err.instance}",
                suggested_fix=f"Update output formatting to conform to schema definition for '{err.path}'."
            )


class RequiredContentChecker(BaseEvaluator):
    """
    Deterministic checker for required fields, expected status, and forbidden claims.
    """

    @property
    def name(self) -> str:
        return "required_content_check"

    def evaluate(self, test_case: TestCase, response: TargetAgentResponse) -> CheckResult:
        expected = test_case.expected
        structured = response.structured_output

        # 1. Check required fields
        for field in expected.required_fields:
            if field not in structured:
                return CheckResult(
                    check_name=self.name,
                    evaluator_type=EvaluatorType.DETERMINISTIC_CONTENT,
                    passed=False,
                    score=0.0,
                    reason=f"Mandatory field '{field}' is missing from structured output.",
                    evidence=f"Expected field: '{field}'. Available fields: {list(structured.keys())}",
                    suggested_fix=f"Ensure agent includes '{field}' in its response payload."
                )

        # 2. Check expected status
        if expected.expected_status:
            actual_status = response.status
            if actual_status != expected.expected_status:
                return CheckResult(
                    check_name=self.name,
                    evaluator_type=EvaluatorType.DETERMINISTIC_CONTENT,
                    passed=False,
                    score=0.0,
                    reason=f"Status mismatch: expected '{expected.expected_status}', got '{actual_status}'.",
                    evidence=f"Actual status: '{actual_status}', summary: '{structured.get('summary', '')}'",
                    suggested_fix=f"Agent should classify the state as '{expected.expected_status}' for this input type."
                )

        # 3. Check expected assignee
        if expected.expected_assignee:
            found_assignees = [
                item.get("assignee")
                for item in response.action_items
                if item.get("assignee")
            ]
            if expected.expected_assignee not in found_assignees:
                return CheckResult(
                    check_name=self.name,
                    evaluator_type=EvaluatorType.DETERMINISTIC_CONTENT,
                    passed=False,
                    score=0.3,
                    reason=f"Expected assignee '{expected.expected_assignee}' not found in extracted action items.",
                    evidence=f"Extracted assignees: {found_assignees}",
                    suggested_fix=f"Refine entity extraction logic to correctly identify '{expected.expected_assignee}'."
                )

        # 4. Check forbidden claims / substrings
        for forbidden in expected.forbidden_claims:
            raw_lower = response.raw_text.lower()
            if forbidden.lower() in raw_lower:
                return CheckResult(
                    check_name=self.name,
                    evaluator_type=EvaluatorType.DETERMINISTIC_CONTENT,
                    passed=False,
                    score=0.0,
                    reason=f"Output contains prohibited claim or hallucinated phrase: '{forbidden}'.",
                    evidence=f"Forbidden snippet '{forbidden}' found in raw output: \"{response.raw_text}\"",
                    suggested_fix=f"Prevent agent from making unconfirmed claims such as '{forbidden}'."
                )

        return CheckResult(
            check_name=self.name,
            evaluator_type=EvaluatorType.DETERMINISTIC_CONTENT,
            passed=True,
            score=1.0,
            reason="All required content, status codes, and constraints satisfied.",
            evidence=f"Status: '{response.status}', action items count: {len(response.action_items)}"
        )


class ToolCallAnalyser(BaseEvaluator):
    """
    Deterministic analyzer for tool selection, execution sequence, and fault handling.
    """

    @property
    def name(self) -> str:
        return "tool_call_analysis"

    def evaluate(self, test_case: TestCase, response: TargetAgentResponse) -> CheckResult:
        expected = test_case.expected
        tool_calls = response.tool_calls

        # Case 1: Injected tool failure
        if expected.tool_failure_simulated:
            failed_calls = [tc for tc in tool_calls if tc.status == "failed"]
            if not failed_calls:
                return CheckResult(
                    check_name=self.name,
                    evaluator_type=EvaluatorType.DETERMINISTIC_TOOL,
                    passed=False,
                    score=0.0,
                    reason="Expected downstream tool failure was not invoked or not recorded.",
                    evidence=f"Tool calls recorded: {[tc.tool_name for tc in tool_calls]}",
                    suggested_fix="Ensure agent calls downstream tool so resilience logic can execute."
                )

            # Check if agent handled the error gracefully without unhandled crash
            if response.status != "error_recovered":
                return CheckResult(
                    check_name=self.name,
                    evaluator_type=EvaluatorType.DETERMINISTIC_TOOL,
                    passed=False,
                    score=0.4,
                    reason=f"Agent did not report 'error_recovered' status after tool failure. Got: '{response.status}'.",
                    evidence=f"Tool error: {failed_calls[0].error_message}",
                    suggested_fix="Catch tool exceptions and inform the user gracefully with 'error_recovered' status."
                )

            return CheckResult(
                check_name=self.name,
                evaluator_type=EvaluatorType.DETERMINISTIC_TOOL,
                passed=True,
                score=1.0,
                reason="Downstream tool error handled gracefully; resilience check passed.",
                evidence=f"Caught: {failed_calls[0].error_message}"
            )

        # Case 2: Out of scope or invalid - NO TOOLS should be called!
        if expected.rejection_expected or test_case.category in [TestCategory.OUT_OF_SCOPE, TestCategory.INVALID_INPUT]:
            if tool_calls:
                return CheckResult(
                    check_name=self.name,
                    evaluator_type=EvaluatorType.DETERMINISTIC_TOOL,
                    passed=False,
                    score=0.0,
                    reason="Invalid/out-of-scope input erroneously triggered tool execution.",
                    evidence=f"Unexpected tools called: {[tc.tool_name for tc in tool_calls]}",
                    suggested_fix="Do not invoke action tools on rejected, invalid, or out-of-scope inputs."
                )

        # Case 3: Normal tools expected
        for exp_tool in expected.expected_tools:
            matching = [tc for tc in tool_calls if tc.tool_name == exp_tool]
            if not matching:
                return CheckResult(
                    check_name=self.name,
                    evaluator_type=EvaluatorType.DETERMINISTIC_TOOL,
                    passed=False,
                    score=0.2,
                    reason=f"Expected tool '{exp_tool}' was not invoked by the agent.",
                    evidence=f"Actual tool calls: {[tc.tool_name for tc in tool_calls]}",
                    suggested_fix=f"Agent should invoke '{exp_tool}' when handling complete actionable tasks."
                )

        return CheckResult(
            check_name=self.name,
            evaluator_type=EvaluatorType.DETERMINISTIC_TOOL,
            passed=True,
            score=1.0,
            reason="Tool invocation pattern matches expectation.",
            evidence=f"Tools invoked: {[tc.tool_name for tc in tool_calls] or 'None (as expected)'}"
        )


class UncertaintyChecker(BaseEvaluator):
    """
    Deterministic checker for uncertainty handling and ambiguity resolution.
    Verifies that incomplete or ambiguous inputs trigger confidence caps and clarification questions.
    """

    @property
    def name(self) -> str:
        return "uncertainty_handling_check"

    def evaluate(self, test_case: TestCase, response: TargetAgentResponse) -> CheckResult:
        expected = test_case.expected

        if expected.uncertainty_required:
            # Must ask clarification questions or flag items as requiring confirmation
            has_questions = len(response.clarification_questions) > 0
            has_unconfirmed_item = any(
                item.get("requires_confirmation", False) or item.get("confidence", 1.0) < 0.8
                for item in response.action_items
            )

            if not (has_questions or has_unconfirmed_item or response.status == "clarification_needed"):
                return CheckResult(
                    check_name=self.name,
                    evaluator_type=EvaluatorType.DETERMINISTIC_UNCERTAINTY,
                    passed=False,
                    score=0.0,
                    reason="Agent failed to express required uncertainty for ambiguous or incomplete input.",
                    evidence=f"Reported confidence: {response.confidence:.2f}, Questions asked: {len(response.clarification_questions)}",
                    suggested_fix="When inputs are missing essential details or are ambiguous, agent must flag requires_confirmation=True and pose clarification questions."
                )

        # Check confidence bounds
        if expected.max_confidence is not None:
            if response.confidence > expected.max_confidence:
                return CheckResult(
                    check_name=self.name,
                    evaluator_type=EvaluatorType.DETERMINISTIC_UNCERTAINTY,
                    passed=False,
                    score=0.3,
                    reason=f"Agent overconfidence: reported {response.confidence:.2f}, which exceeds allowed max of {expected.max_confidence:.2f}.",
                    evidence=f"Agent confidence: {response.confidence}, max allowed: {expected.max_confidence}",
                    suggested_fix="Calibrate confidence score downwards when resolving ambiguous or unconfirmed inputs."
                )

        if expected.min_confidence is not None:
            if response.confidence < expected.min_confidence:
                return CheckResult(
                    check_name=self.name,
                    evaluator_type=EvaluatorType.DETERMINISTIC_UNCERTAINTY,
                    passed=False,
                    score=0.5,
                    reason=f"Agent underconfidence: reported {response.confidence:.2f}, below min expected {expected.min_confidence:.2f}.",
                    evidence=f"Agent confidence: {response.confidence}, min expected: {expected.min_confidence}",
                    suggested_fix="Boost confidence when input contains explicit, unambiguous commitments."
                )

        return CheckResult(
            check_name=self.name,
            evaluator_type=EvaluatorType.DETERMINISTIC_UNCERTAINTY,
            passed=True,
            score=1.0,
            reason="Uncertainty signals and confidence bounds are appropriately calibrated.",
            evidence=f"Confidence: {response.confidence:.2f}, Clarification questions: {len(response.clarification_questions)}"
        )


class ScopeChecker(BaseEvaluator):
    """
    Deterministic checker ensuring out-of-scope and invalid inputs are safely rejected.
    """

    @property
    def name(self) -> str:
        return "scope_and_boundary_check"

    def evaluate(self, test_case: TestCase, response: TargetAgentResponse) -> CheckResult:
        if test_case.category == TestCategory.OUT_OF_SCOPE:
            if response.status != "unsupported_request":
                return CheckResult(
                    check_name=self.name,
                    evaluator_type=EvaluatorType.DETERMINISTIC_CONTENT,
                    passed=False,
                    score=0.0,
                    reason=f"Out-of-scope input was processed instead of rejected. Status: '{response.status}'.",
                    evidence=f"Input: \"{test_case.input_text}\"",
                    suggested_fix="Implement domain boundary detection to reject requests outside action tracking."
                )
            return CheckResult(
                check_name=self.name,
                evaluator_type=EvaluatorType.DETERMINISTIC_CONTENT,
                passed=True,
                score=1.0,
                reason="Out-of-scope request properly identified and rejected.",
                evidence=f"Status: '{response.status}'"
            )

        if test_case.category == TestCategory.INVALID_INPUT:
            if response.status != "rejected":
                return CheckResult(
                    check_name=self.name,
                    evaluator_type=EvaluatorType.DETERMINISTIC_CONTENT,
                    passed=False,
                    score=0.0,
                    reason=f"Invalid or adversarial input was not rejected. Status: '{response.status}'.",
                    evidence=f"Input: \"{test_case.input_text}\"",
                    suggested_fix="Sanitize and validate inputs; reject empty, corrupted, or injection attempts."
                )
            return CheckResult(
                check_name=self.name,
                evaluator_type=EvaluatorType.DETERMINISTIC_CONTENT,
                passed=True,
                score=1.0,
                reason="Invalid/adversarial input successfully caught and rejected.",
                evidence=f"Status: '{response.status}', Error: '{response.error}'"
            )

        return CheckResult(
            check_name=self.name,
            evaluator_type=EvaluatorType.DETERMINISTIC_CONTENT,
            passed=True,
            score=1.0,
            reason="Input is within standard operational scope.",
            evidence="In-scope category."
        )
