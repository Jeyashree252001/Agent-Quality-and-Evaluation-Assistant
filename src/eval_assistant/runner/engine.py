import time
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from ..models import (
    TestCase,
    TargetAgentResponse,
    CheckResult,
    TestCaseEvaluation,
    EvaluationSummary,
    EvaluatorType,
)
from ..config import config
from ..target_agent.agent import ActionExtractionAgent
from ..evaluators.deterministic import (
    JSONSchemaValidator,
    RequiredContentChecker,
    ToolCallAnalyser,
    UncertaintyChecker,
    ScopeChecker,
)
from ..evaluators.grounding import UnsupportedClaimChecker
from ..evaluators.model_judge import ModelBasedJudge


class EvaluationEngine:
    """
    Core Evaluation Engine.
    
    Orchestrates test execution, applies deterministic verification first,
    runs bounded model evaluation, and aggregates evidence into actionable reports.
    """

    def __init__(self, target_agent: Optional[ActionExtractionAgent] = None):
        self.target_agent = target_agent or ActionExtractionAgent()
        
        # Deterministic evaluators
        self.deterministic_evaluators = [
            JSONSchemaValidator(),
            RequiredContentChecker(),
            ToolCallAnalyser(),
            UncertaintyChecker(),
            ScopeChecker(),
            UnsupportedClaimChecker(),
        ]
        
        # Model judge
        self.model_judge = ModelBasedJudge()

    def evaluate_test_case(self, test_case: TestCase) -> TestCaseEvaluation:
        """Run a single test case against the target agent and evaluate all aspects."""
        start_eval_time = time.time()

        # Step 1: Execute target agent
        response = self.target_agent.process(
            input_text=test_case.input_text,
            behavior_mode=test_case.target_behavior_mode or "default",
            simulate_tool_error=test_case.expected.tool_failure_simulated
        )

        checks: List[CheckResult] = []
        failure_reasons: List[str] = []
        suggested_improvements: List[str] = []
        requires_human_review = False

        # Step 2: Run deterministic evaluators
        for evaluator in self.deterministic_evaluators:
            check = evaluator.evaluate(test_case, response)
            checks.append(check)
            if not check.passed:
                failure_reasons.append(f"[{check.check_name}] {check.reason}")
                if check.suggested_fix:
                    suggested_improvements.append(check.suggested_fix)

        deterministic_passed = len(failure_reasons) == 0

        # Step 3: Run safeguarded model judge
        # Only run model evaluation if configured and test case is not a hard input rejection
        if config.eval_mode in ["hybrid", "model_only"]:
            model_check = self.model_judge.evaluate(test_case, response)
            checks.append(model_check)

            if model_check.requires_human_review:
                requires_human_review = True

            # Principle: Model judge cannot overturn a deterministic failure
            if deterministic_passed and not model_check.passed:
                failure_reasons.append(f"[{model_check.check_name}] {model_check.reason}")
                if model_check.suggested_fix:
                    suggested_improvements.append(model_check.suggested_fix)

        overall_passed = len(failure_reasons) == 0
        eval_latency = (time.time() - start_eval_time) * 1000

        # Deduplicate suggestions
        unique_improvements = list(dict.fromkeys(suggested_improvements))

        return TestCaseEvaluation(
            test_case=test_case,
            agent_response=response,
            overall_passed=overall_passed,
            checks=checks,
            failure_reasons=failure_reasons,
            suggested_improvements=unique_improvements,
            requires_human_review=requires_human_review,
            evaluation_time_ms=eval_latency
        )

    def run_suite(self, test_cases: List[TestCase]) -> EvaluationSummary:
        """Execute and aggregate results across an entire test suite."""
        evaluations: List[TestCaseEvaluation] = []
        total_tests = len(test_cases)
        passed_tests = 0
        failed_tests = 0
        review_needed = 0

        results_by_category: Dict[str, Dict[str, Any]] = {}

        for tc in test_cases:
            res = self.evaluate_test_case(tc)
            evaluations.append(res)

            cat_key = tc.category.value
            if cat_key not in results_by_category:
                results_by_category[cat_key] = {"total": 0, "passed": 0, "failed": 0, "review_needed": 0}

            results_by_category[cat_key]["total"] += 1

            if res.overall_passed:
                passed_tests += 1
                results_by_category[cat_key]["passed"] += 1
            else:
                failed_tests += 1
                results_by_category[cat_key]["failed"] += 1

            if res.requires_human_review:
                review_needed += 1
                results_by_category[cat_key]["review_needed"] += 1

        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0.0

        return EvaluationSummary(
            timestamp=datetime.now(timezone.utc).isoformat(),
            eval_mode=config.eval_mode,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            review_needed=review_needed,
            pass_rate_percentage=round(pass_rate, 2),
            results_by_category=results_by_category,
            evaluations=evaluations
        )
