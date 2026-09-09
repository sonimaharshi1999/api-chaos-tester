# API Chaos Tester - Intelligent API Fuzz Testing
# Author: Maharshi Soni | License: MIT
"""
Test case generator.
Orchestrates strategy selection and test case generation for a set
of API endpoints, with optional ML-based prioritization.
"""

from __future__ import annotations

from typing import Optional

from api_chaos_tester.models import ApiEndpoint, ChaosTestCase
from api_chaos_tester.predictor import FailurePredictor
from api_chaos_tester.strategies import ALL_STRATEGIES
from api_chaos_tester.strategies.base import BaseStrategy


def generate_test_cases(
    endpoints: list[ApiEndpoint],
    strategies: list[type[BaseStrategy]] | None = None,
    predictor: FailurePredictor | None = None,
    max_cases_per_endpoint: Optional[int] = None,
) -> list[ChaosTestCase]:
    """
    Generate chaos test cases for a list of API endpoints.

    Args:
        endpoints: The API endpoints to generate tests for.
        strategies: Specific strategy classes to use; defaults to all.
        predictor: Optional ML predictor for scoring and prioritization.
        max_cases_per_endpoint: Cap the number of tests per endpoint.

    Returns:
        A list of generated (and optionally prioritized) test cases.
    """
    if strategies is None:
        strategies = ALL_STRATEGIES

    all_cases: list[ChaosTestCase] = []

    for endpoint in endpoints:
        endpoint_cases: list[ChaosTestCase] = []
        for strategy_cls in strategies:
            strategy = strategy_cls()
            cases = strategy.generate(endpoint)
            endpoint_cases.extend(cases)

        # Score and sort if predictor is available
        if predictor is not None:
            endpoint_cases = predictor.score_and_sort(endpoint_cases)

        # Apply per-endpoint cap
        if max_cases_per_endpoint is not None:
            endpoint_cases = endpoint_cases[:max_cases_per_endpoint]

        all_cases.extend(endpoint_cases)

    return all_cases
