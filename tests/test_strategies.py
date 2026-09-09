# API Chaos Tester - Intelligent API Fuzz Testing
# Author: Maharshi Soni | License: MIT
"""Tests for chaos testing strategies."""

from __future__ import annotations

from api_chaos_tester.models import (
    ApiEndpoint,
    ChaosStrategy,
    HttpMethod,
    ParameterLocation,
    ParameterType,
)
from api_chaos_tester.strategies.boundary import BoundaryValueStrategy
from api_chaos_tester.strategies.null_injection import NullInjectionStrategy
from api_chaos_tester.strategies.overflow import OverflowStrategy
from api_chaos_tester.strategies.special_chars import SpecialCharacterStrategy
from api_chaos_tester.strategies.type_confusion import TypeConfusionStrategy
from api_chaos_tester.strategies.unicode_stress import UnicodeStressStrategy


class TestBoundaryValueStrategy:
    def test_generates_cases_for_integer_params(
        self, simple_get_endpoint: ApiEndpoint
    ) -> None:
        strategy = BoundaryValueStrategy()
        cases = strategy.generate(simple_get_endpoint)
        assert len(cases) > 0
        assert all(c.strategy == ChaosStrategy.BOUNDARY_VALUES for c in cases)

    def test_numeric_boundary_values(
        self, path_param_endpoint: ApiEndpoint
    ) -> None:
        strategy = BoundaryValueStrategy()
        cases = strategy.generate(path_param_endpoint)
        descriptions = [c.description for c in cases]
        # Should include zero, negative, and extreme values
        assert any("zero" in d for d in descriptions)
        assert any("negative" in d for d in descriptions)

    def test_string_boundary_values(
        self, simple_get_endpoint: ApiEndpoint
    ) -> None:
        strategy = BoundaryValueStrategy()
        cases = strategy.generate(simple_get_endpoint)
        descriptions = [c.description for c in cases]
        assert any("empty string" in d for d in descriptions)
        assert any("long string" in d for d in descriptions)

    def test_array_boundary_values(
        self, post_endpoint: ApiEndpoint
    ) -> None:
        strategy = BoundaryValueStrategy()
        cases = strategy.generate(post_endpoint)
        descriptions = [c.description for c in cases]
        assert any("empty array" in d for d in descriptions)


class TestTypeConfusionStrategy:
    def test_generates_type_mismatch_cases(
        self, simple_get_endpoint: ApiEndpoint
    ) -> None:
        strategy = TypeConfusionStrategy()
        cases = strategy.generate(simple_get_endpoint)
        assert len(cases) > 0
        assert all(c.strategy == ChaosStrategy.TYPE_CONFUSION for c in cases)

    def test_integer_gets_string_confusion(
        self, path_param_endpoint: ApiEndpoint
    ) -> None:
        strategy = TypeConfusionStrategy()
        cases = strategy.generate(path_param_endpoint)
        descriptions = [c.description for c in cases]
        assert any("string instead of int" in d for d in descriptions)

    def test_body_params_get_confusion(
        self, post_endpoint: ApiEndpoint
    ) -> None:
        strategy = TypeConfusionStrategy()
        cases = strategy.generate(post_endpoint)
        # Should have cases for body params too
        body_cases = [c for c in cases if c.body is not None]
        assert len(body_cases) > 0


class TestNullInjectionStrategy:
    def test_generates_null_cases(
        self, simple_get_endpoint: ApiEndpoint
    ) -> None:
        strategy = NullInjectionStrategy()
        cases = strategy.generate(simple_get_endpoint)
        assert len(cases) > 0
        assert all(c.strategy == ChaosStrategy.NULL_INJECTION for c in cases)

    def test_required_params_get_null_tests(
        self, simple_get_endpoint: ApiEndpoint
    ) -> None:
        strategy = NullInjectionStrategy()
        cases = strategy.generate(simple_get_endpoint)
        descriptions = [c.description for c in cases]
        assert any("explicit null" in d for d in descriptions)
        assert any("string 'null'" in d for d in descriptions)

    def test_omit_all_required_test(
        self, simple_get_endpoint: ApiEndpoint
    ) -> None:
        strategy = NullInjectionStrategy()
        cases = strategy.generate(simple_get_endpoint)
        descriptions = [c.description for c in cases]
        assert any("omit all required" in d for d in descriptions)


class TestUnicodeStressStrategy:
    def test_generates_unicode_cases(
        self, simple_get_endpoint: ApiEndpoint
    ) -> None:
        strategy = UnicodeStressStrategy()
        cases = strategy.generate(simple_get_endpoint)
        assert len(cases) > 0
        assert all(c.strategy == ChaosStrategy.UNICODE_STRESS for c in cases)

    def test_no_cases_without_string_params(
        self, path_param_endpoint: ApiEndpoint
    ) -> None:
        strategy = UnicodeStressStrategy()
        cases = strategy.generate(path_param_endpoint)
        # path_param_endpoint has only an integer param
        assert len(cases) == 0

    def test_includes_emoji_and_rtl(
        self, simple_get_endpoint: ApiEndpoint
    ) -> None:
        strategy = UnicodeStressStrategy()
        cases = strategy.generate(simple_get_endpoint)
        descriptions = [c.description for c in cases]
        assert any("emoji" in d for d in descriptions)
        assert any("RTL" in d for d in descriptions)


class TestSpecialCharacterStrategy:
    def test_generates_injection_cases(
        self, simple_get_endpoint: ApiEndpoint
    ) -> None:
        strategy = SpecialCharacterStrategy()
        cases = strategy.generate(simple_get_endpoint)
        assert len(cases) > 0
        descriptions = [c.description for c in cases]
        assert any("SQL injection" in d for d in descriptions)
        assert any("XSS" in d for d in descriptions)


class TestOverflowStrategy:
    def test_generates_overflow_for_body_endpoints(
        self, post_endpoint: ApiEndpoint
    ) -> None:
        strategy = OverflowStrategy()
        cases = strategy.generate(post_endpoint)
        assert len(cases) > 0
        descriptions = [c.description for c in cases]
        assert any("deeply nested" in d for d in descriptions)

    def test_generates_overflow_for_query_params(
        self, simple_get_endpoint: ApiEndpoint
    ) -> None:
        strategy = OverflowStrategy()
        cases = strategy.generate(simple_get_endpoint)
        descriptions = [c.description for c in cases]
        # Should have long query param test
        assert any("extremely long" in d for d in descriptions)
