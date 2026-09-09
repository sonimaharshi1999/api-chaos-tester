# API Chaos Tester - Intelligent API Fuzz Testing
# Author: Maharshi Soni | License: MIT
"""
Null injection chaos strategy.
Tests how the API handles null, None, and missing values across
required and optional parameters.
"""

from __future__ import annotations

from api_chaos_tester.models import (
    ApiEndpoint,
    ApiParameter,
    ChaosStrategy,
    ChaosTestCase,
    ParameterLocation,
)
from api_chaos_tester.strategies.base import BaseStrategy


class NullInjectionStrategy(BaseStrategy):
    """Generate tests that inject null/missing values into parameters."""

    strategy_type = ChaosStrategy.NULL_INJECTION

    def generate(self, endpoint: ApiEndpoint) -> list[ChaosTestCase]:
        cases: list[ChaosTestCase] = []

        for param in endpoint.parameters:
            cases.extend(self._null_cases_for_param(endpoint, param))

        # Also test omitting all required parameters at once
        required_params = [p for p in endpoint.parameters if p.required]
        if required_params:
            names = ", ".join(p.name for p in required_params)
            cases.append(
                self._make_case(
                    endpoint,
                    description=f"Null injection: omit all required params ({names})",
                    parameters={},
                    body=None,
                    expected_behavior="Should return 400/422 for missing required fields",
                )
            )

        return cases

    def _null_cases_for_param(
        self, endpoint: ApiEndpoint, param: ApiParameter
    ) -> list[ChaosTestCase]:
        cases: list[ChaosTestCase] = []
        null_variants: list[tuple[str, object]] = [
            ("explicit null", None),
            ("empty string", ""),
            ("string 'null'", "null"),
            ("string 'undefined'", "undefined"),
        ]

        for label, value in null_variants:
            if param.location == ParameterLocation.BODY:
                params: dict = {}
                body: object = {param.name: value}
            else:
                params = {param.name: value}
                body = None

            expected = (
                "Should return 400/422 for null on required field"
                if param.required
                else "Should handle gracefully or use default"
            )

            cases.append(
                self._make_case(
                    endpoint,
                    description=f"Null injection: {param.name} = {label}",
                    parameters=params,
                    body=body,
                    expected_behavior=expected,
                )
            )

        return cases
