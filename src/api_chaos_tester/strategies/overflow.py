# API Chaos Tester - Intelligent API Fuzz Testing
# Author: Maharshi Soni | License: MIT
"""
Overflow chaos strategy.
Tests how the API handles extremely large payloads, deeply nested
structures, and resource exhaustion scenarios.
"""

from __future__ import annotations

from api_chaos_tester.models import (
    ApiEndpoint,
    ChaosStrategy,
    ChaosTestCase,
    ParameterLocation,
    ParameterType,
)
from api_chaos_tester.strategies.base import BaseStrategy


class OverflowStrategy(BaseStrategy):
    """Generate tests that attempt to overflow various limits."""

    strategy_type = ChaosStrategy.OVERFLOW

    def generate(self, endpoint: ApiEndpoint) -> list[ChaosTestCase]:
        cases: list[ChaosTestCase] = []

        # Test oversized body payloads for endpoints that accept bodies
        body_params = [
            p for p in endpoint.parameters
            if p.location == ParameterLocation.BODY
        ]
        if body_params:
            cases.extend(self._body_overflow_cases(endpoint))

        # Test oversized query strings
        query_params = [
            p for p in endpoint.parameters
            if p.location == ParameterLocation.QUERY
        ]
        if query_params:
            target = query_params[0]
            cases.append(
                self._make_case(
                    endpoint,
                    description=f"Overflow: extremely long query param {target.name}",
                    parameters={target.name: "X" * 100_000},
                    expected_behavior="Should return 413/414 or handle gracefully",
                )
            )

        # Test many duplicate parameters
        if query_params:
            target = query_params[0]
            cases.append(
                self._make_case(
                    endpoint,
                    description=f"Overflow: many duplicate values for {target.name}",
                    parameters={target.name: ",".join(["val"] * 1000)},
                    expected_behavior="Should handle repeated params gracefully",
                )
            )

        return cases

    def _body_overflow_cases(
        self, endpoint: ApiEndpoint
    ) -> list[ChaosTestCase]:
        cases: list[ChaosTestCase] = []

        # Deeply nested object
        nested: dict = {"level": "deepest"}
        for _ in range(50):
            nested = {"nested": nested}

        cases.append(
            self._make_case(
                endpoint,
                description="Overflow: deeply nested JSON (50 levels)",
                body=nested,
                expected_behavior="Should return 400 or handle depth limit",
            )
        )

        # Very large JSON body
        large_body = {f"key_{i}": "value" * 100 for i in range(500)}
        cases.append(
            self._make_case(
                endpoint,
                description="Overflow: large JSON body (500 keys)",
                body=large_body,
                expected_behavior="Should return 413 or handle size limit",
            )
        )

        return cases
