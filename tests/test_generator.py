# API Chaos Tester - Intelligent API Fuzz Testing
# Author: Maharshi Soni | License: MIT
"""Tests for the test case generator orchestrator."""

from __future__ import annotations

from api_chaos_tester.generator import generate_test_cases
from api_chaos_tester.models import ApiEndpoint
from api_chaos_tester.predictor import FailurePredictor
from api_chaos_tester.strategies.boundary import BoundaryValueStrategy
from api_chaos_tester.strategies.null_injection import NullInjectionStrategy


class TestGenerateTestCases:
    def test_generates_cases_for_endpoint(
        self, simple_get_endpoint: ApiEndpoint
    ) -> None:
        cases = generate_test_cases([simple_get_endpoint])
        assert len(cases) > 0

    def test_respects_strategy_filter(
        self, simple_get_endpoint: ApiEndpoint
    ) -> None:
        cases = generate_test_cases(
            [simple_get_endpoint],
            strategies=[BoundaryValueStrategy],
        )
        from api_chaos_tester.models import ChaosStrategy
        assert all(c.strategy == ChaosStrategy.BOUNDARY_VALUES for c in cases)

    def test_respects_max_cases_per_endpoint(
        self, simple_get_endpoint: ApiEndpoint
    ) -> None:
        cases = generate_test_cases(
            [simple_get_endpoint],
            max_cases_per_endpoint=5,
        )
        assert len(cases) <= 5

    def test_uses_predictor_for_sorting(
        self, simple_get_endpoint: ApiEndpoint
    ) -> None:
        predictor = FailurePredictor()
        cases = generate_test_cases(
            [simple_get_endpoint],
            predictor=predictor,
        )
        # All cases should have a failure_probability set
        assert all(c.failure_probability > 0 for c in cases)
        # They should be sorted by descending probability
        probs = [c.failure_probability for c in cases]
        assert probs == sorted(probs, reverse=True)

    def test_multiple_endpoints(
        self,
        simple_get_endpoint: ApiEndpoint,
        post_endpoint: ApiEndpoint,
    ) -> None:
        cases = generate_test_cases([simple_get_endpoint, post_endpoint])
        # Should have cases for both endpoints
        paths = {c.endpoint.path for c in cases}
        assert "/items" in paths

    def test_empty_endpoints_list(self) -> None:
        cases = generate_test_cases([])
        assert cases == []
