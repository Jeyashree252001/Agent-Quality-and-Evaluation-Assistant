import argparse
import sys
from pathlib import Path

from .config import config
from .runner.loader import load_test_suite
from .runner.engine import EvaluationEngine
from .reporting.terminal import TerminalReporter
from .reporting.json_reporter import JSONReporter
from .reporting.html_reporter import HTMLReporter


def main():
    parser = argparse.ArgumentParser(
        description="Agent Quality and Evaluation Assistant - Robust Agent Testing Framework"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: run
    run_parser = subparsers.add_parser("run", help="Run full evaluation test suite")
    run_parser.add_argument(
        "--suite",
        type=str,
        default=str(config.default_test_suite),
        help="Path to JSON test suite file (defaults to data/test_cases.json)"
    )
    run_parser.add_argument(
        "--mode",
        type=str,
        choices=["hybrid", "deterministic_only", "offline_simulation"],
        default=config.eval_mode,
        help="Evaluation execution mode"
    )
    run_parser.add_argument(
        "--output-dir",
        type=str,
        default=str(config.output_dir),
        help="Directory where evaluation reports (HTML & JSON) are saved"
    )

    # Command: inspect
    inspect_parser = subparsers.add_parser("inspect", help="Inspect detailed evaluation of a specific test case")
    inspect_parser.add_argument(
        "test_id",
        type=str,
        help="ID of the test case to execute and inspect (e.g. TC-08-UNSUPPORTED-ASSUMPTION)"
    )
    inspect_parser.add_argument(
        "--suite",
        type=str,
        default=str(config.default_test_suite),
        help="Path to JSON test suite file"
    )

    args = parser.parse_args()

    terminal_reporter = TerminalReporter()
    json_reporter = JSONReporter()
    html_reporter = HTMLReporter()

    if args.command == "run" or args.command is None:
        suite_path = getattr(args, "suite", str(config.default_test_suite))
        out_dir = Path(getattr(args, "output_dir", str(config.output_dir)))
        if hasattr(args, "mode"):
            config.eval_mode = args.mode

        terminal_reporter.console.print(f"[bold cyan]Loading test suite from:[/bold cyan] {suite_path}")
        try:
            test_cases = load_test_suite(suite_path)
        except Exception as e:
            terminal_reporter.console.print(f"[bold red]Failed to load test suite:[/bold red] {e}")
            sys.exit(1)

        engine = EvaluationEngine()
        summary = engine.run_suite(test_cases)

        # Print console output
        terminal_reporter.print_summary(summary)

        # Generate JSON & HTML reports
        json_path = out_dir / "evaluation_report.json"
        html_path = out_dir / "evaluation_report.html"

        json_reporter.save(summary, json_path)
        html_reporter.generate(summary, html_path)

        terminal_reporter.console.print(f"\n[bold green][OK] JSON Report generated:[/bold green] {json_path}")
        terminal_reporter.console.print(f"[bold green][OK] Interactive HTML Report generated:[/bold green] {html_path}\n")

    elif args.command == "inspect":
        suite_path = getattr(args, "suite", str(config.default_test_suite))
        test_id = args.test_id

        try:
            test_cases = load_test_suite(suite_path)
        except Exception as e:
            terminal_reporter.console.print(f"[bold red]Failed to load test suite:[/bold red] {e}")
            sys.exit(1)

        target_case = next((tc for tc in test_cases if tc.id.lower() == test_id.lower()), None)
        if not target_case:
            terminal_reporter.console.print(f"[bold red]Test case '{test_id}' not found in suite.[/bold red]")
            sys.exit(1)

        engine = EvaluationEngine()
        evaluation = engine.evaluate_test_case(target_case)
        terminal_reporter.print_inspection(evaluation)


if __name__ == "__main__":
    main()
