# API Chaos Tester - Intelligent API Fuzz Testing
# Author: Maharshi Soni | License: MIT
"""
CLI interface using Click and Rich.
Provides commands for running chaos tests against APIs specified
via OpenAPI specs or direct URL targeting.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from api_chaos_tester.generator import generate_test_cases
from api_chaos_tester.models import ChaosTestCase
from api_chaos_tester.parser import parse_openapi_spec
from api_chaos_tester.predictor import FailurePredictor
from api_chaos_tester.reporter import generate_html_report, print_summary
from api_chaos_tester.runner import run_tests_sync
from api_chaos_tester.strategies import ALL_STRATEGIES

console = Console()


@click.group()
@click.version_option(version="1.0.0", prog_name="API Chaos Tester")
def main() -> None:
    """API Chaos Tester - Intelligent API Fuzz Testing.

    Generate and run chaos test cases against your APIs to find bugs
    before your users do.
    """
    pass


@main.command()
@click.argument("spec_path", type=click.Path(exists=True))
@click.option("--base-url", "-u", required=True, help="Base URL of the target API")
@click.option("--concurrency", "-c", default=5, help="Max concurrent requests")
@click.option("--timeout", "-t", default=10.0, help="Request timeout in seconds")
@click.option("--max-per-endpoint", "-m", default=None, type=int, help="Max tests per endpoint")
@click.option("--report", "-r", default=None, type=click.Path(), help="Output HTML report path")
@click.option("--strategy", "-s", multiple=True, help="Specific strategies to use")
def run(
    spec_path: str,
    base_url: str,
    concurrency: int,
    timeout: float,
    max_per_endpoint: int | None,
    report: str | None,
    strategy: tuple[str, ...],
) -> None:
    """Run chaos tests against an API defined by an OpenAPI spec."""
    console.print("[bold blue]API Chaos Tester[/bold blue]", justify="center")
    console.print()

    # Parse spec
    with console.status("[bold green]Parsing OpenAPI spec..."):
        try:
            endpoints = parse_openapi_spec(spec_path)
        except Exception as exc:
            console.print(f"[red]Error parsing spec: {exc}[/red]")
            sys.exit(1)

    console.print(f"Found [bold]{len(endpoints)}[/bold] endpoints")

    # Filter strategies if specified
    selected_strategies = ALL_STRATEGIES
    if strategy:
        strategy_names = {s.strategy_type.value for s in ALL_STRATEGIES}
        for s in strategy:
            if s not in strategy_names:
                console.print(f"[red]Unknown strategy: {s}[/red]")
                console.print(f"Available: {', '.join(sorted(strategy_names))}")
                sys.exit(1)
        selected_strategies = [
            cls for cls in ALL_STRATEGIES
            if cls.strategy_type.value in strategy  # type: ignore[attr-defined]
        ]

    # Generate test cases
    predictor = FailurePredictor()
    with console.status("[bold green]Generating chaos test cases..."):
        test_cases = generate_test_cases(
            endpoints,
            strategies=selected_strategies,
            predictor=predictor,
            max_cases_per_endpoint=max_per_endpoint,
        )

    console.print(f"Generated [bold]{len(test_cases)}[/bold] test cases")
    console.print()

    # Run tests with progress
    console.print("[bold]Running chaos tests...[/bold]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        task = progress.add_task("Testing...", total=len(test_cases))

        def update_progress(completed: int, total: int) -> None:
            progress.update(task, completed=completed)

        suite = run_tests_sync(
            test_cases=test_cases,
            base_url=base_url,
            concurrency=concurrency,
            timeout=timeout,
            api_name=Path(spec_path).stem,
            progress_callback=update_progress,
        )

    console.print()
    print_summary(suite, console)

    # Generate HTML report if requested
    if report:
        report_path = generate_html_report(suite, report)
        console.print(f"\n[green]HTML report saved to: {report_path}[/green]")

    # Feed results back to predictor for future runs
    predictor.learn(suite.results)

    # Exit code based on results
    if suite.failed > 0 or suite.errors > 0:
        sys.exit(1)


@main.command()
@click.argument("spec_path", type=click.Path(exists=True))
@click.option("--max-per-endpoint", "-m", default=None, type=int, help="Max tests per endpoint")
def preview(spec_path: str, max_per_endpoint: int | None) -> None:
    """Preview generated test cases without running them."""
    console.print("[bold blue]API Chaos Tester - Preview Mode[/bold blue]")
    console.print()

    with console.status("[bold green]Parsing OpenAPI spec..."):
        endpoints = parse_openapi_spec(spec_path)

    console.print(f"Found [bold]{len(endpoints)}[/bold] endpoints")

    predictor = FailurePredictor()
    test_cases = generate_test_cases(
        endpoints,
        predictor=predictor,
        max_cases_per_endpoint=max_per_endpoint,
    )

    console.print(f"Generated [bold]{len(test_cases)}[/bold] test cases\n")

    from rich.table import Table

    table = Table(title="Generated Test Cases", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("Endpoint", width=25)
    table.add_column("Strategy", width=18)
    table.add_column("Description", max_width=45)
    table.add_column("P(fail)", justify="right", width=8)

    for i, tc in enumerate(test_cases[:50], 1):  # Show first 50
        endpoint_str = f"{tc.endpoint.method.value} {tc.endpoint.path}"
        table.add_row(
            str(i),
            endpoint_str,
            tc.strategy.value,
            tc.description[:45],
            f"{tc.failure_probability:.2f}",
        )

    console.print(table)

    if len(test_cases) > 50:
        console.print(f"\n[dim]... and {len(test_cases) - 50} more test cases[/dim]")


@main.command()
def strategies() -> None:
    """List available chaos testing strategies."""
    from rich.table import Table

    table = Table(title="Available Chaos Strategies")
    table.add_column("Strategy", style="bold")
    table.add_column("Description")

    descriptions: dict[str, str] = {
        "boundary_values": "Tests extreme and edge-case values for numeric/string/array params",
        "type_confusion": "Sends values of the wrong type to test validation",
        "null_injection": "Injects null, empty, and undefined values",
        "unicode_stress": "Tests unusual Unicode sequences, RTL, zero-width chars, emoji",
        "special_characters": "Tests SQL/XSS/shell injection and special char handling",
        "overflow": "Tests oversized payloads and deeply nested structures",
    }

    for cls in ALL_STRATEGIES:
        name = cls.strategy_type.value  # type: ignore[attr-defined]
        desc = descriptions.get(name, "")
        table.add_row(name, desc)

    console.print(table)


if __name__ == "__main__":
    main()
