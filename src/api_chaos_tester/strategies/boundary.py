# API Chaos Tester - Intelligent API Fuzz Testing
# Author: Maharshi Soni | License: MIT
"""
Boundary value chaos strategy.
Generates test cases using extreme and edge-case values for numeric,
string, and array parameters to probe off-by-one errors and range checks.
"""

from __future__ import annotations

import sys

from api_chaos_tester.models import (
    ApiEndpoint,
    ApiParameter,
    ChaosStrategy,
    ChaosTestCase,
    ParameterLocation,
    ParameterType,
)
from api_chaos_tester.strategies.base import BaseStrategy


class BoundaryValueStrategy(BaseStrategy):
    """Generate tests with boundary / extreme values for each parameter."""

    strategy_type = ChaosStrategy.BOUNDARY_VALUES

    def generate(self, endpoint: ApiEndpoint) -> list[ChaosTestCase]:
        cases: list[ChaosTestCase] = []
        for param in endpoint.parameters:
            cases.extend(self._cases_for_param(endpoint, param))
        return cases

    def _cases_for_param(
        self, endpoint: ApiEndpoint, param: ApiParameter
    ) -> list[ChaosTestCase]:
        cases: list[ChaosTestCase] = []

        if param.param_type in (ParameterType.INTEGER, ParameterType.NUMBER):
            cases.extend(self._numeric_boundaries(endpoint, param))
        elif param.param_type == ParameterType.STRING:
            cases.extend(self._string_boundaries(endpoint, param))
        elif param.param_type == ParameterType.ARRAY:
            cases.extend(self._array_boundaries(endpoint, param))

        return cases

    def _numeric_boundaries(
        self, endpoint: ApiEndpoint, param: ApiParameter
    ) -> list[ChaosTestCase]:
        values: list[tuple[str, object]] = [
            ("zero", 0),
            ("negative one", -1),
            ("max int32", 2**31 - 1),
            ("min int32", -(2**31)),
            ("max int64", 2**63 - 1),
            ("float max", sys.float_info.max),
        ]

        if param.min_value is not None:
            values.append(("min - 1", param.min_value - 1))
            values.append(("exact min", param.min_value))
        if param.max_value is not None:
            values.append(("max + 1", param.max_value + 1))
            values.append(("exact max", param.max_value))

        cases: list[ChaosTestCase] = []
        for label, value in values:
            params, body = self._build_payload(param, value)
            cases.append(
                self._make_case(
                    endpoint,
                    description=f"Boundary: {param.name} = {label} ({value})",
                    parameters=params,
                    body=body,
                    expected_behavior="Should return 400 or handle gracefully",
                )
            )
        return cases

    def _string_boundaries(
        self, endpoint: ApiEndpoint, param: ApiParameter
    ) -> list[ChaosTestCase]:
        values: list[tuple[str, str]] = [
            ("empty string", ""),
            ("single char", "a"),
            ("long string (10k chars)", "A" * 10_000),
            ("whitespace only", "   \t\n  "),
        ]

        if param.max_length is not None:
            values.append(
                (f"max_length + 1", "X" * (param.max_length + 1))
            )
        if param.min_length is not None and param.min_length > 0:
            values.append(
                (f"min_length - 1", "X" * (param.min_length - 1))
            )

        cases: list[ChaosTestCase] = []
        for label, value in values:
            params, body = self._build_payload(param, value)
            cases.append(
                self._make_case(
                    endpoint,
                    description=f"Boundary: {param.name} = {label}",
                    parameters=params,
                    body=body,
                    expected_behavior="Should return 400/422 or handle gracefully",
                )
            )
        return cases

    def _array_boundaries(
        self, endpoint: ApiEndpoint, param: ApiParameter
    ) -> list[ChaosTestCase]:
        values: list[tuple[str, object]] = [
            ("empty array", []),
            ("single element", ["item"]),
            ("large array (1000)", list(range(1000))),
            ("nested arrays", [[[["deep"]]]]),
        ]

        cases: list[ChaosTestCase] = []
        for label, value in values:
            params, body = self._build_payload(param, value)
            cases.append(
                self._make_case(
                    endpoint,
                    description=f"Boundary: {param.name} = {label}",
                    parameters=params,
                    body=body,
                    expected_behavior="Should return 400/422 or handle gracefully",
                )
            )
        return cases

    @staticmethod
    def _build_payload(
        param: ApiParameter, value: object
    ) -> tuple[dict, object]:
        """Route a value to either query/path params or body depending on location."""
        if param.location == ParameterLocation.BODY:
            return {}, {param.name: value}
        return {param.name: value}, None
