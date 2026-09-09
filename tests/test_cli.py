# API Chaos Tester - Intelligent API Fuzz Testing
# Author: Maharshi Soni | License: MIT
"""Tests for the CLI interface."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from api_chaos_tester.cli import main


class TestCLI:
    def test_version(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "1.0.0" in result.output

    def test_strategies_command(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["strategies"])
        assert result.exit_code == 0
        assert "boundary_values" in result.output
        assert "type_confusion" in result.output
        assert "null_injection" in result.output

    def test_preview_command(self, sample_spec_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["preview", str(sample_spec_path)])
        assert result.exit_code == 0
        assert "endpoints" in result.output
        assert "test cases" in result.output

    def test_preview_with_max_per_endpoint(self, sample_spec_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            main, ["preview", str(sample_spec_path), "-m", "3"]
        )
        assert result.exit_code == 0

    def test_run_missing_spec(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["run", "/nonexistent.yaml", "-u", "http://localhost"])
        assert result.exit_code != 0
