# API Chaos Tester - Intelligent API Fuzz Testing
# Author: Maharshi Soni | License: MIT
"""
Type confusion chaos strategy.
Sends values of the wrong type for each parameter to test whether
the API properly validates and rejects mismatched types.
"""

from __future__ import annotations

from api_chaos_tester.models import (
    ApiEndpoint,
    ApiParameter,
    ChaosStrategy,
    ChaosTestCase,
    ParameterLocation,
    ParameterType,
)
from api_chaos_tester.strategies.base import BaseStrategy


# For each expected type, a list of (label, wrong-value) pairs
_CONFUSION_MAP: dict[ParameterType, list[tuple[str, object]]] = {
    ParameterType.INTEGER: [
        ("string instead of int", "not_a_number"),
        ("float instead of int", 3.14),
        ("boolean instead of int", True),
        ("array instead of int", [1, 2, 3]),
        ("object instead of int", {"value": 42}),
    ],
    ParameterType.NUMBER: [
        ("string instead of number", "NaN"),
        ("boolean instead of number", False),
        ("array instead of number", [1.5]),
        ("infinity string", "Infinity"),
    ],
    ParameterType.STRING: [
        ("integer instead of string", 42),
        ("boolean instead of string", True),
        ("array instead of string", ["a", "b"]),
        ("object instead of string", {"key": "value"}),
        ("null instead of string", None),
    ],
    ParameterType.BOOLEAN: [
        ("string instead of bool", "yes"),
        ("integer instead of bool", 1),
        ("string 'true'", "true"),
        ("integer 2 (not 0/1)", 2),
    ],
    ParameterType.ARRAY: [
        ("string instead of array", "not_an_array"),
        ("integer instead of array", 42),
        ("object instead of array", {"items": []}),
    ],
    ParameterType.OBJECT: [
        ("string instead of object", "not_an_object"),
        ("array instead of object", [1, 2, 3]),
        ("integer instead of object", 99),
    ],
}


class TypeConfusionStrategy(BaseStrategy):
    """Generate tests that send mismatched types for each parameter."""

    strategy_type = ChaosStrategy.TYPE_CONFUSION

    def generate(self, endpoint: ApiEndpoint) -> list[ChaosTestCase]:
        cases: list[ChaosTestCase] = []

        for param in endpoint.parameters:
            confusion_values = _CONFUSION_MAP.get(param.param_type, [])
            for label, wrong_value in confusion_values:
                if param.location == ParameterLocation.BODY:
                    params: dict = {}
                    body: object = {param.name: wrong_value}
                else:
                    params = {param.name: wrong_value}
                    body = None

                cases.append(
                    self._make_case(
                        endpoint,
                        description=(
                            f"Type confusion: {param.name} expects "
                            f"{param.param_type.value}, sent {label}"
                        ),
                        parameters=params,
                        body=body,
                        expected_behavior="Should return 400/422 for type mismatch",
                    )
                )

        return cases
