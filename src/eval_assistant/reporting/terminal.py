from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from ..models import EvaluationSummary, TestCaseEvaluation


class TerminalReporter:
    """Rich console reporter for evaluation summaries and test inspection."""

    def __init__(self):
        self.console = Console()

    def print_summary(self, summary: EvaluationSummary):
        """Render high-level summary and category breakdown tables."""
        self.console.print("\n")
        banner = Panel(
            Text("AGENT QUALITY & EVALUATION ASSISTANT\nStructured Multi-Tier Evaluation Report", justify="center", style="bold cyan"),
            subtitle=f"Mode: {summary.eval_mode.upper()} | Timestamp: {summary.timestamp[:19]}",
            border_style="cyan"
        )
        self.console.print(banner)

        # Overview Table
        overview_table = Table(title="Overall Test Execution Metrics", show_header=True, header_style="bold magenta")
        overview_table.add_column("Total Tests", justify="center")
        overview_table.add_column("Passed", justify="center", style="bold green")
        overview_table.add_column("Failed", justify="center", style="bold red")
        overview_table.add_column("Review Required", justify="center", style="bold yellow")
        overview_table.add_column("Pass Rate", justify="center", style="bold cyan")

        overview_table.add_row(
            str(summary.total_tests),
            str(summary.passed_tests),
            str(summary.failed_tests),
            str(summary.review_needed),
            f"{summary.pass_rate_percentage:.1f}%"
        )
        self.console.print(overview_table)

        # Category Breakdown Table
        cat_table = Table(title="Category Breakdown (7 Required Categories)", show_header=True, header_style="bold blue")
        cat_table.add_column("Test Category", style="bold")
        cat_table.add_column("Total", justify="center")
        cat_table.add_column("Passed", justify="center", style="green")
        cat_table.add_column("Failed", justify="center", style="red")
        cat_table.add_column("Review Needed", justify="center", style="yellow")
        cat_table.add_column("Category Pass Rate", justify="right")

        for cat, stats in summary.results_by_category.items():
            tot = stats["total"]
            p = stats["passed"]
            rate = (p / tot * 100) if tot > 0 else 0.0
            rate_style = "green" if rate >= 80 else ("yellow" if rate >= 50 else "red")
            cat_table.add_row(
                cat,
                str(tot),
                str(p),
                str(stats["failed"]),
                str(stats.get("review_needed", 0)),
                f"[{rate_style}]{rate:.1f}%[/{rate_style}]"
            )
        self.console.print(cat_table)

        # Test Cases List
        test_list_table = Table(title="Individual Test Case Outcomes", show_header=True, header_style="bold")
        test_list_table.add_column("ID", style="dim")
        test_list_table.add_column("Category")
        test_list_table.add_column("Title")
        test_list_table.add_column("Status", justify="center")
        test_list_table.add_column("Human Review", justify="center")

        for ev in summary.evaluations:
            status_text = "[bold green]PASS[/bold green]" if ev.overall_passed else "[bold red]FAIL[/bold red]"
            review_text = "[bold yellow]YES[/bold yellow]" if ev.requires_human_review else "NO"
            test_list_table.add_row(
                ev.test_case.id,
                ev.test_case.category.value,
                ev.test_case.title,
                status_text,
                review_text
            )
        self.console.print(test_list_table)

    def print_inspection(self, evaluation: TestCaseEvaluation):
        """Render detailed forensic inspection of a single test case evaluation."""
        tc = evaluation.test_case
        resp = evaluation.agent_response

        status_style = "bold green" if evaluation.overall_passed else "bold red"
        status_word = "PASSED" if evaluation.overall_passed else "FAILED"

        self.console.print(f"\n[{status_style}]============================================================================[/{status_style}]")
        self.console.print(f"[{status_style}]TEST CASE INSPECTION: {tc.id} - {tc.title} ({status_word})[/{status_style}]")
        self.console.print(f"[{status_style}]============================================================================[/{status_style}]")

        self.console.print(f"[bold cyan]Category:[/bold cyan] {tc.category.value}")
        self.console.print(f"[bold cyan]Rationale:[/bold cyan] {tc.rationale}")
        self.console.print(f"[bold cyan]Source Input:[/bold cyan]\n  \"{tc.input_text}\"")

        self.console.print(f"\n[bold yellow]Agent Output:[/bold yellow]")
        self.console.print(f"  [bold]Raw Text:[/bold] \"{resp.raw_text}\"")
        self.console.print(f"  [bold]Status:[/bold] '{resp.status}' | [bold]Confidence:[/bold] {resp.confidence:.2f}")
        if resp.clarification_questions:
            self.console.print(f"  [bold]Clarifications Asked:[/bold] {resp.clarification_questions}")
        if resp.tool_calls:
            tools_str = ", ".join(f"{tc.tool_name}({tc.args}) -> {tc.status}" for tc in resp.tool_calls)
            self.console.print(f"  [bold]Tool Invocations:[/bold] {tools_str}")

        # Check results
        self.console.print(f"\n[bold magenta]Evaluation Checks Breakdown:[/bold magenta]")
        check_table = Table(show_header=True, header_style="bold")
        check_table.add_column("Evaluator")
        check_table.add_column("Type")
        check_table.add_column("Result", justify="center")
        check_table.add_column("Score", justify="right")
        check_table.add_column("Reason / Evidence")

        for ch in evaluation.checks:
            result_badge = "[green]OK[/green]" if ch.passed else "[red]FAIL[/red]"
            check_table.add_row(
                ch.check_name,
                ch.evaluator_type.value,
                result_badge,
                f"{ch.score:.2f}",
                f"{ch.reason}\n[dim]{ch.evidence[:120]}[/dim]" if ch.evidence else ch.reason
            )
        self.console.print(check_table)

        if evaluation.failure_reasons:
            self.console.print(f"\n[bold red]Primary Failure Reasons:[/bold red]")
            for r in evaluation.failure_reasons:
                self.console.print(f"  * {r}", style="red")

        if evaluation.suggested_improvements:
            self.console.print(f"\n[bold green]Actionable Recommendations for Agent Developers:[/bold green]")
            for imp in evaluation.suggested_improvements:
                self.console.print(f"  -> {imp}", style="green")

        if evaluation.requires_human_review:
            self.console.print(f"\n[bold yellow][!] ATTENTION: This test case is flagged for HUMAN-IN-THE-LOOP review.[/bold yellow]")
            self.console.print(f"[dim]Reason: Evaluator uncertainty or borderline scoring necessitates human oversight.[/dim]\n")
