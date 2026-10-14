import re
from typing import List, Set
from ..models import TestCase, TargetAgentResponse, CheckResult, EvaluatorType
from .base import BaseEvaluator


class UnsupportedClaimChecker(BaseEvaluator):
    """
    Deterministic Grounding & Unsupported Assumption Evaluator.
    
    Verifies that all entities, commitments, and assignees asserted by the target agent
    are verifiably supported by the source context, and flags unwarranted inferential leaps
    (e.g., turning a statement of hesitation into a confirmed assignment).
    """

    DEFERRAL_PATTERNS = [
        r"more information is needed before anyone can take responsibility",
        r"before anyone can take responsibility",
        r"need(s)? more info(rmation)?",
        r"nobody agreed",
        r"not yet decided",
        r"pending further",
        r"has not been assigned",
        r"unconfirmed",
        r"might take a look",
    ]

    @property
    def name(self) -> str:
        return "unsupported_claim_and_grounding_check"

    def evaluate(self, test_case: TestCase, response: TargetAgentResponse) -> CheckResult:
        input_text = test_case.input_text
        input_lower = input_text.lower()
        expected = test_case.expected

        # 1. Check forbidden assignees (explicit test constraint)
        for forbidden in expected.forbidden_assignees:
            for item in response.action_items:
                assignee = item.get("assignee")
                if assignee and forbidden.lower() in assignee.lower():
                    evidence = f"Source input: \"{input_text}\"\nAgent assigned: \"{assignee}\" to task \"{item.get('task')}\""
                    return CheckResult(
                        check_name=self.name,
                        evaluator_type=EvaluatorType.DETERMINISTIC_GROUNDING,
                        passed=False,
                        score=0.0,
                        reason=f"Unsupported Assumption: Agent assigned '{assignee}', but source text does not support assigning this person.",
                        evidence=evidence,
                        suggested_fix=f"Do not infer responsibility when source indicates ambiguity or prerequisite conditions. '{assignee}' should not be designated as owner without confirmation."
                    )

        # 2. Check assignee grounding in source text
        for item in response.action_items:
            assignee = item.get("assignee")
            if assignee:
                # Assignee name must at least appear in source text
                if assignee.lower() not in input_lower:
                    return CheckResult(
                        check_name=self.name,
                        evaluator_type=EvaluatorType.DETERMINISTIC_GROUNDING,
                        passed=False,
                        score=0.0,
                        reason=f"Hallucinated Assignee: '{assignee}' does not appear anywhere in the input text.",
                        evidence=f"Extracted assignee: '{assignee}' vs Source Text: \"{input_text}\"",
                        suggested_fix="Restrict entity extraction strictly to entities explicitly identified in the input."
                    )

        # 3. Detect unwarranted commitment under deferral / conditional context
        # (The Mika Cost Estimate scenario from the assignment package)
        has_deferral = any(re.search(pat, input_lower) for pat in self.DEFERRAL_PATTERNS)
        if has_deferral:
            for item in response.action_items:
                assignee = item.get("assignee")
                requires_conf = item.get("requires_confirmation", False)
                item_conf = item.get("confidence", 1.0)

                if assignee and (not requires_conf or item_conf > 0.7):
                    evidence = (
                        f"Source input: \"{input_text}\"\n"
                        f"Agent generated claim: \"{response.raw_text}\"\n"
                        f"Extracted action item: assignee={assignee}, requires_confirmation={requires_conf}, confidence={item_conf}"
                    )
                    return CheckResult(
                        check_name=self.name,
                        evaluator_type=EvaluatorType.DETERMINISTIC_GROUNDING,
                        passed=False,
                        score=0.0,
                        reason="Unsupported Commitment: Source context contains explicit deferral/hesitation, but agent asserted a confirmed commitment.",
                        evidence=evidence,
                        suggested_fix="When source text indicates prerequisite information or hesitation, mark action items with requires_confirmation=True and do not lock in assignees."
                    )

        # 4. Check for hallucinated action tasks
        # Ensure task has some lexical token overlap with input text
        input_tokens = set(re.findall(r"\w+", input_lower))
        # Filter common stopwords
        stopwords = {"the", "a", "an", "is", "and", "or", "to", "for", "in", "on", "at", "by", "will", "be"}
        meaningful_input_tokens = input_tokens - stopwords

        for item in response.action_items:
            task_tokens = set(re.findall(r"\w+", item.get("task", "").lower())) - stopwords
            if meaningful_input_tokens and not (task_tokens & meaningful_input_tokens):
                return CheckResult(
                    check_name=self.name,
                    evaluator_type=EvaluatorType.DETERMINISTIC_GROUNDING,
                    passed=False,
                    score=0.2,
                    reason=f"Ungrounded Action Item: Task '{item.get('task')}' shares no semantic vocabulary with the source input.",
                    evidence=f"Task tokens: {task_tokens} vs Input tokens: {meaningful_input_tokens}",
                    suggested_fix="Ensure extracted tasks are derived directly from input context rather than fabricated."
                )

        return CheckResult(
            check_name=self.name,
            evaluator_type=EvaluatorType.DETERMINISTIC_GROUNDING,
            passed=True,
            score=1.0,
            reason="All extracted entities, assignees, and commitments are grounded in the source text.",
            evidence=f"Verified against source text (Length: {len(input_text)} chars)."
        )
