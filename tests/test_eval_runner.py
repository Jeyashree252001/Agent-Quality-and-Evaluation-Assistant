import pytest
from pathlib import Path
from src.eval_assistant.runner.loader import load_test_suite
from src.eval_assistant.runner.engine import EvaluationEngine
from src.eval_assistant.reporting.json_reporter import JSONReporter
from src.eval_assistant.reporting.html_reporter import HTMLReporter


def test_loader_loads_test_suite():
    data_file = Path("data/test_cases.json")
    test_cases = load_test_suite(data_file)
    assert len(test_cases) >= 7
    categories = {tc.category.value for tc in test_cases}
    # Ensure all 7 required categories are present
    expected_categories = {
        "normal_input",
        "incomplete_input",
        "ambiguous_input",
        "out_of_scope",
        "invalid_input",
        "tool_failure",
        "unsupported_assumption",
    }
    assert expected_categories.issubset(categories)


def test_evaluation_engine_suite_run(tmp_path):
    data_file = Path("data/test_cases.json")
    test_cases = load_test_suite(data_file)

    engine = EvaluationEngine()
    summary = engine.run_suite(test_cases)

    assert summary.total_tests == len(test_cases)
    assert summary.passed_tests > 0
    # Note: TC-09 is specifically designed to test that the evaluator catches the hallucination regression!
    assert summary.failed_tests >= 1

    # Test report generation
    json_path = tmp_path / "report.json"
    html_path = tmp_path / "report.html"

    json_reporter = JSONReporter()
    html_reporter = HTMLReporter()

    json_reporter.save(summary, json_path)
    html_reporter.generate(summary, html_path)

    assert json_path.exists()
    assert html_path.exists()
    assert html_path.stat().st_size > 1000
