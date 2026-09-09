# API Chaos Tester - Intelligent API Fuzz Testing
# Author: Maharshi Soni | License: MIT
"""
Special character chaos strategy.
Tests injection of SQL, shell, and script-like payloads to verify
the API properly sanitizes or rejects dangerous input.
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


_SPECIAL_PAYLOADS: list[tuple[str, str]] = [
    ("SQL injection (basic)", "' OR '1'='1"),
    ("SQL injection (union)", "' UNION SELECT * FROM users--"),
    ("SQL injection (drop)", "'; DROP TABLE users;--"),
    ("XSS script tag", "<script>alert('xss')</script>"),
    ("XSS img onerror", '<img src=x onerror=alert(1)>'),
    ("Shell injection (pipe)", "| ls -la"),
    ("Shell injection (semicolon)", "; cat /etc/passwd"),
    ("Path traversal", "../../../etc/passwd"),
    ("LDAP injection", "*)(&"),
    ("XML injection", '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'),
    ("Template injection (Jinja)", "{{7*7}}"),
    ("Template injection (ERB)", "<%= 7*7 %>"),
    ("CRLF injection", "header\r\nX-Injected: true"),
    ("JSON injection", '{"__proto__": {"admin": true}}'),
]


class SpecialCharacterStrategy(BaseStrategy):
    """Generate tests with special characters and injection payloads."""

    strategy_type = ChaosStrategy.SPECIAL_CHARACTERS

    def generate(self, endpoint: ApiEndpoint) -> list[ChaosTestCase]:
        cases: list[ChaosTestCase] = []

        string_params = [
            p
            for p in endpoint.parameters
            if p.param_type == ParameterType.STRING
        ]

        if not string_params:
            return cases

        target = string_params[0]

        for label, payload in _SPECIAL_PAYLOADS:
            if target.location == ParameterLocation.BODY:
                params: dict = {}
                body: object = {target.name: payload}
            else:
                params = {target.name: payload}
                body = None

            cases.append(
                self._make_case(
                    endpoint,
                    description=f"Special chars: {target.name} = {label}",
                    parameters=params,
                    body=body,
                    expected_behavior="Should sanitize/reject without 500",
                )
            )

        return cases
