# API Chaos Tester - Intelligent API Fuzz Testing
# Author: Maharshi Soni | License: MIT
"""
Unicode stress chaos strategy.
Tests how the API handles unusual Unicode sequences, RTL text,
zero-width characters, emoji, and other encoding edge cases.
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


_UNICODE_PAYLOADS: list[tuple[str, str]] = [
    ("null byte", "test\x00value"),
    ("RTL override", "‮Right-to-Left"),
    ("zero-width joiners", "a‍‍‍b"),
    ("emoji sequence", "\U0001f468‍\U0001f469‍\U0001f467‍\U0001f466"),
    ("CJK characters", "中文测试"),
    ("Arabic text", "مرحبا"),
    ("combining diacriticals", "é́́́́"),
    ("Zalgo text", "H̶̢̒ë̷̛́l̴̜͐l̵̠͗o̶̩͒"),
    ("homoglyph attack", "АВС"),  # Cyrillic that looks like ABC
    ("byte order mark", "﻿test"),
    ("line separators", "line1 line2 line3"),
    ("math symbols", "∞ ∅ ∀x ∃y"),
    ("surrogate-like", "\ud800"),  # Lone surrogate (may cause issues)
]


class UnicodeStressStrategy(BaseStrategy):
    """Generate tests with Unicode edge cases for string parameters."""

    strategy_type = ChaosStrategy.UNICODE_STRESS

    def generate(self, endpoint: ApiEndpoint) -> list[ChaosTestCase]:
        cases: list[ChaosTestCase] = []

        string_params = [
            p
            for p in endpoint.parameters
            if p.param_type == ParameterType.STRING
        ]

        if not string_params:
            return cases

        # Apply each Unicode payload to the first string parameter
        # (applying to all would create a combinatorial explosion)
        target = string_params[0]

        for label, payload in _UNICODE_PAYLOADS:
            if target.location == ParameterLocation.BODY:
                params: dict = {}
                body: object = {target.name: payload}
            else:
                params = {target.name: payload}
                body = None

            cases.append(
                self._make_case(
                    endpoint,
                    description=f"Unicode stress: {target.name} = {label}",
                    parameters=params,
                    body=body,
                    expected_behavior="Should handle Unicode gracefully without 500",
                )
            )

        return cases
