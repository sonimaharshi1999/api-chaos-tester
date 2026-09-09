# API Chaos Tester - Intelligent API Fuzz Testing
# Author: Maharshi Soni | License: MIT
"""Tests for the report generator."""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path

from rich.console import Console

from api_chaos_tester.models import (
    ApiEndpoint,
    ChaosStrategy,
    ChaosTestCase,
    HttpMethod,
    TestResult,
    TestStatus,
    TestSuiteResult,
)
from api_chaos_tester.reporter import generate_html_report, print_summary


def _make_suite() -> TestSuiteResult:
    """Create a sample test suite result for testing."""
    endpoint = ApiEndpoint(path="/test", method=HttpMethod.GET)
    cases_and_statuses = [
        (ChaosStrategy.BOUNDARY_VALUES, TestStatus.PASSED, 200),
        (ChaosStrategy.TYPE_CONFUSION, TestStatus.FAILED, 500),
        (ChaosStrategy.NULL_INJECTION, TestStatus.PASSED, 400),
        (ChaosStrategy.UNICODE_STRESS, TestStatus.ERROR, None),
    ]
    results = []
    for strategy, status, code in cases_and_statuses:
        tc = ChaosTestCase(
            endpoint=endpoint,
            strategy=strategy,
            description=f"Test {strategy.value}",
        )
        results.append(
            TestResult(
                test_case=tc,
                status=status,
                status_code=code,
                response_time_ms=50.0,
                error_message="Connection failed" if status == TestStatus.ERROR else None,
                reproduction_curl=f"curl -X GET http://test.local/test",
            )
        )

    return TestSuiteResult(
        api_name="Test API",
        base_url="http://test.local",
        total_tests=4,
        passed=2,
        failed=1,
        errors=1,
        results=results,
        start_time=datetime(2025, 1, 1, 12, 0, 0),
        end_time=datetime(2025, 1, 1, 12, 0, 5),
        duration_seconds=5.0,
    )


class TestPrintSummary:
    def test_prints_without_error(self) -> None:
        suite = _make_suite()
        console = Console(file=open(tempfile.mktemp(suffix=".txt"), "w"))
        # Should not raise
        print_summary(suite, console)

    def test_handles_empty_suite(self) -> None:
        suite = TestSuiteResult()
        console = Console(file=open(tempfile.mktemp(suffix=".txt"), "w"))
        print_summary(suite, console)


class TestHtmlReport:
    def test_generates_html_file(self, templates_dir: Path) -> None:
        suite = _make_suite()
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "report.html"
            result_path = generate_html_report(suite, output, templates_dir)
            assert result_path.exists()
            content = result_path.read_text(encoding="utf-8")
            assert "Test API" in content
            assert "Chaos Test Report" in content

    def test_report_contains_strategy_breakdown(self, templates_dir: Path) -> None:
        suite = _make_suite()
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "report.html"
            generate_html_report(suite, output, templates_dir)
            content = output.read_text(encoding="utf-8")
            assert "boundary_values" in content
            assert "type_confusion" in content

    def test_report_contains_failure_details(self, templates_dir: Path) -> None:
        suite = _make_suite()
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "report.html"
            generate_html_report(suite, output, templates_dir)
            content = output.read_text(encoding="utf-8")
            assert "Failure Analysis" in content
            assert "curl" in content

    def test_creates_output_directory(self, templates_dir: Path) -> None:
        suite = _make_suite()
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "nested" / "dir" / "report.html"
            generate_html_report(suite, output, templates_dir)
            assert output.exists()
