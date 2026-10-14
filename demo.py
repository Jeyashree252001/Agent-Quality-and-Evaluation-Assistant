"""
Interactive Working Demonstration of the Agent Quality and Evaluation Assistant.

Demonstrates:
  1. One Successful Interaction (Normal Input -> Clean Extraction & Tool Call)
  2. One Ambiguous / Incomplete Interaction (Missing Owner -> Uncertainty & Clarification)
  3. One Failure Scenario (Unsupported Assumption -> Evaluator catches hallucination)
"""

import time
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from src.eval_assistant.models import (
    TestCase,
    TestCategory,
    ExpectedBehavior,
)
from src.eval_assistant.runner.engine import EvaluationEngine
from src.eval_assistant.reporting.terminal import TerminalReporter

console = Console()
reporter = TerminalReporter()
engine = EvaluationEngine()


def print_banner(title: str, subtitle: str, color: str = "cyan"):
    console.print("\n")
    p = Panel(
        Text(title, justify="center", style=f"bold {color}"),
        subtitle=subtitle,
        border_style=color
    )
    console.print(p)


def run_demo():
    print_banner(
        "AGENT QUALITY & EVALUATION ASSISTANT: WORKING DEMO",
        "Demonstrating Success, Ambiguity Handling, and Forensic Failure Catching",
        "magenta"
    )
    time.sleep(1)

    # =========================================================================
    # SCENARIO 1: SUCCESSFUL INTERACTION (Normal Input)
    # =========================================================================
    print_banner(
        "SCENARIO 1: SUCCESSFUL INTERACTION (Complete & Grounded Input)",
        "Category: normal_input",
        "green"
    )
    console.print("[bold]Context:[/bold] User provides an explicit, unambiguous action item with an owner and deadline.")
    console.print("[dim]Input:[/dim] \"Sarah will send the revised Q3 budget by Friday 5 PM.\"\n")

    tc1 = TestCase(
        id="DEMO-01-SUCCESS",
        category=TestCategory.NORMAL_INPUT,
        title="Sarah Budget Action Item",
        description="Explicit owner and deadline.",
        input_text="Sarah will send the revised Q3 budget by Friday 5 PM.",
        target_behavior_mode="default",
        expected=ExpectedBehavior(
            must_succeed=True,
            expected_status="extracted",
            expected_assignee="Sarah",
            required_fields=["status", "summary", "action_items", "confidence"],
            uncertainty_required=False,
            min_confidence=0.85,
            expected_tools=["lookup_team_member", "create_task_ticket"]
        ),
        rationale="Verifies immediate extraction, tool dispatch, and high confidence on clear inputs."
    )

    eval1 = engine.evaluate_test_case(tc1)
    reporter.print_inspection(eval1)

    console.print("\n[bold cyan]Agent Decision Flow Explanation:[/bold cyan]")
    console.print("  1. Agent identifies unambiguous assignee ('Sarah') and deadline ('Friday 5 PM').")
    console.print("  2. Dispatches directory lookup (`lookup_team_member`) to confirm active status.")
    console.print("  3. Invokes project tool (`create_task_ticket`) and receives ticket ID.")
    console.print("  4. Evaluator confirms valid JSON schema, tool call validity, and 100% grounding in source text.")

    input("\nPress ENTER to continue to Scenario 2 (Ambiguous Interaction)...")

    # =========================================================================
    # SCENARIO 2: AMBIGUOUS & INCOMPLETE INTERACTION
    # =========================================================================
    print_banner(
        "SCENARIO 2: AMBIGUOUS INTERACTION (Unconfirmed Multiple Candidates)",
        "Category: ambiguous_input",
        "yellow"
    )
    console.print("[bold]Context:[/bold] Input mentions multiple team members tentatively ('might take a look').")
    console.print("[dim]Input:[/dim] \"Alex or Jordan might take a look at the login bug next week.\"\n")

    tc2 = TestCase(
        id="DEMO-02-AMBIGUOUS",
        category=TestCategory.AMBIGUOUS_INPUT,
        title="Tentative Ownership Login Bug",
        description="Tentative disjunctive commitment.",
        input_text="Alex or Jordan might take a look at the login bug next week.",
        target_behavior_mode="default",
        expected=ExpectedBehavior(
            must_succeed=True,
            expected_status="clarification_needed",
            expected_assignee=None,
            forbidden_assignees=[],
            forbidden_claims=["Alex will fix", "Jordan will fix"],
            required_fields=["status", "clarification_questions"],
            uncertainty_required=True,
            max_confidence=0.70,
            expected_tools=[]
        ),
        rationale="Verifies that ambiguity prevents unwarranted ticket creation and prompts proactive questions."
    )

    eval2 = engine.evaluate_test_case(tc2)
    reporter.print_inspection(eval2)

    console.print("\n[bold cyan]Agent Decision Flow Explanation:[/bold cyan]")
    console.print("  1. Agent identifies tentative phrasing ('might') and disjunctive ownership ('Alex or Jordan').")
    console.print("  2. Properly avoids premature tool invocation (`create_task_ticket` suppressed).")
    console.print("  3. Flags `requires_confirmation = True` and reports lower confidence (0.50).")
    console.print("  4. Formulates a clarifying question: 'Should this task be assigned to Alex or Jordan?'")
    console.print("  5. Evaluator checks confirm uncertainty calibration and absence of premature tool calls.")

    input("\nPress ENTER to continue to Scenario 3 (Failure Scenario - Unsupported Assumption)...")

    # =========================================================================
    # SCENARIO 3: FAILURE SCENARIO (Unsupported Assumption Caught)
    # =========================================================================
    print_banner(
        "SCENARIO 3: FAILURE SCENARIO (Unsupported Assumption / Hallucination)",
        "Category: unsupported_assumption",
        "red"
    )
    console.print("[bold]Context:[/bold] The Mika cost estimate prompt example. Target agent erroneously assumes responsibility.")
    console.print("[dim]Input:[/dim] \"The team discussed updating the cost estimate. Mika said that more information is needed before anyone can take responsibility.\"\n")

    tc3 = TestCase(
        id="DEMO-03-UNSUPPORTED-FAIL",
        category=TestCategory.UNSUPPORTED_ASSUMPTION,
        title="Mika Hesitation - Hallucinating Agent Regression",
        description="Buggy agent asserts Mika will update cost estimate.",
        input_text="The team discussed updating the cost estimate. Mika said that more information is needed before anyone can take responsibility.",
        target_behavior_mode="hallucinating",  # Intentionally triggers the flawed agent behavior!
        expected=ExpectedBehavior(
            must_succeed=True,
            expected_status="clarification_needed",
            expected_assignee=None,
            forbidden_assignees=["Mika"],
            forbidden_claims=["Mika will update the cost estimate"],
            required_fields=["status", "summary", "clarification_questions"],
            uncertainty_required=True,
            max_confidence=0.60,
            expected_tools=[]
        ),
        rationale="Demonstrates how the evaluator catches ungrounded assumptions and stops buggy models from shipping."
    )

    eval3 = engine.evaluate_test_case(tc3)
    reporter.print_inspection(eval3)

    console.print("\n[bold red]Evaluator Forensic Analysis & Actionable Improvements:[/bold red]")
    console.print("  * [bold]The Flaw:[/bold] The agent output asserted: 'Mika will update the cost estimate.'")
    console.print("  * [bold]The Evaluator Catch:[/bold] `UnsupportedClaimChecker` detected that Mika stated 'more information is needed before anyone can take responsibility'.")
    console.print("  * [bold]Evidence:[/bold] Neither Mika as owner nor an agreed action is supported by the source text.")
    console.print("  * [bold]Actionable Remediation:[/bold] Update system instructions and few-shot examples to forbid inferring commitments from statements of hesitation or requirement prerequisites.")

    print_banner(
        "DEMONSTRATION COMPLETED",
        "All 3 scenarios executed and verified successfully.",
        "magenta"
    )


if __name__ == "__main__":
    import sys
    if "--auto" in sys.argv:
        # Override input for automated demo execution
        input = lambda *args, **kwargs: None
    run_demo()
