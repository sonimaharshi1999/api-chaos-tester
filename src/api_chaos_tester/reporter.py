# API Chaos Tester - Intelligent API Fuzz Testing
# Author: Maharshi Soni | License: MIT
"""
Test report generator.
Produces rich terminal output and HTML reports from test suite results
using Jinja2 templates and the Rich library.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from api_chaos_tester.models import TestResult, TestStatus, TestSuiteResult


_STATUS_COLORS: dict[TestStatus, str] = {
    TestStatus.PASSED: "green",
    TestStatus.FAILED: "red",
    TestStatus.ERROR: "yellow",
    TestStatus.SKIPPED: "dim",
    TestStatus.TIMEOUT: "magenta",
}

_STATUS_ICONS: dict[TestStatus, str] = {
    TestStatus.PASSED: "[green]PASS[/green]",
    TestStatus.FAILED: "[red]FAIL[/red]",
    TestStatus.ERROR: "[yellow]ERR [/yellow]",
    TestStatus.SKIPPED: "[dim]SKIP[/dim]",
    TestStatus.TIMEOUT: "[magenta]TIME[/magenta]",
}


def print_summary(suite: TestSuiteResult, console: Console | None = None) -> None:
    """Print a rich summary table of the test suite results to the terminal."""
    if console is None:
        console = Console()

    # Header panel
    header_text = Text()
    header_text.append(f"API Chaos Test Results: {suite.api_name}\n", style="bold")
    header_text.append(f"Target: {suite.base_url}\n", style="dim")
    header_text.append(
        f"Duration: {suite.duration_seconds:.2f}s | "
        f"Tests: {suite.total_tests}"
    )
    console.print(Panel(header_text, title="Chaos Test Report", border_style="blue"))

    # Summary stats
    stats_table = Table(show_header=False, box=None, padding=(0, 2))
    stats_table.add_column("Metric", style="bold")
    stats_table.add_column("Value", justify="right")

    stats_table.add_row("Total Tests", str(suite.total_tests))
    stats_table.add_row("[green]Passed[/green]", str(suite.passed))
    stats_table.add_row("[red]Failed[/red]", str(suite.failed))
    stats_table.add_row("[yellow]Errors[/yellow]", str(suite.errors))
    stats_table.add_row("[magenta]Timeouts[/magenta]", str(suite.timeouts))
    stats_table.add_row("[dim]Skipped[/dim]", str(suite.skipped))
    stats_table.add_row("Pass Rate", f"{suite.pass_rate:.1f}%")
    stats_table.add_row("Failure Rate", f"{suite.failure_rate:.1f}%")

    console.print(stats_table)
    console.print()

    # Detailed results table
    detail_table = Table(
        title="Test Results",
        show_lines=True,
        title_style="bold",
    )
    detail_table.add_column("#", style="dim", width=4)
    detail_table.add_column("Status", width=6)
    detail_table.add_column("Strategy", width=18)
    detail_table.add_column("Description", max_width=50)
    detail_table.add_column("Code", justify="center", width=6)
    detail_table.add_column("Time", justify="right", width=10)

    for i, result in enumerate(suite.results, 1):
        status_text = _STATUS_ICONS.get(result.status, str(result.status.value))
        code = str(result.status_code) if result.status_code else "-"
        time_str = f"{result.response_time_ms:.0f}ms"

        detail_table.add_row(
            str(i),
            status_text,
            result.test_case.strategy.value,
            result.test_case.description[:50],
            code,
            time_str,
        )

    console.print(detail_table)

    # Print failures and errors in detail
    failures = [
        r for r in suite.results
        if r.status in (TestStatus.FAILED, TestStatus.ERROR)
    ]
    if failures:
        console.print()
        console.print(
            Panel("[red bold]Failures & Errors[/red bold]", border_style="red")
        )
        for result in failures:
            _print_failure_detail(result, console)


def _print_failure_detail(result: TestResult, console: Console) -> None:
    """Print detailed information about a failed test."""
    tc = result.test_case
    console.print(f"\n[red bold]{tc.description}[/red bold]")
    console.print(f"  Strategy: {tc.strategy.value}")
    console.print(f"  Endpoint: {tc.endpoint.method.value} {tc.endpoint.path}")
    if result.status_code:
        console.print(f"  Status Code: {result.status_code}")
    if result.error_message:
        console.print(f"  Error: {result.error_message}")
    if result.response_body:
        body_preview = result.response_body[:200]
        console.print(f"  Response: {body_preview}")
    console.print(f"\n  [dim]Reproduce with:[/dim]")
    console.print(f"  [cyan]{result.reproduction_curl}[/cyan]")


def generate_html_report(
    suite: TestSuiteResult,
    output_path: str | Path,
    template_dir: str | Path | None = None,
) -> Path:
    """
    Generate an HTML test report from suite results.

    Args:
        suite: The test suite results to report on.
        output_path: Where to write the HTML file.
        template_dir: Directory containing the report.html template.
                      Defaults to the templates/ dir relative to this package.

    Returns:
        Path to the generated HTML file.
    """
    if template_dir is None:
        template_dir = Path(__file__).parent.parent.parent / "templates"

    template_dir = Path(template_dir)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=True,
    )
    template = env.get_template("report.html")

    # Group results by strategy
    by_strategy: dict[str, list[TestResult]] = {}
    for result in suite.results:
        key = result.test_case.strategy.value
        by_strategy.setdefault(key, []).append(result)

    # Group failures by endpoint
    failures_by_endpoint: dict[str, list[TestResult]] = {}
    for result in suite.results:
        if result.status in (TestStatus.FAILED, TestStatus.ERROR):
            key = f"{result.test_case.endpoint.method.value} {result.test_case.endpoint.path}"
            failures_by_endpoint.setdefault(key, []).append(result)

    html = template.render(
        suite=suite,
        by_strategy=by_strategy,
        failures_by_endpoint=failures_by_endpoint,
        TestStatus=TestStatus,
    )

    output_path.write_text(html, encoding="utf-8")
    return output_path
