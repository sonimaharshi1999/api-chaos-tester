# API Chaos Tester - Intelligent API Fuzz Testing
# Author: Maharshi Soni | License: MIT
"""Tests for Pydantic data models."""

from __future__ import annotations

from api_chaos_tester.models import (
    ApiEndpoint,
    ApiParameter,
    ChaosStrategy,
    ChaosTestCase,
    HttpMethod,
    ParameterLocation,
    ParameterType,
    TestResult,
    TestStatus,
    TestSuiteResult,
)


class TestApiParameter:
    def test_default_values(self) -> None:
        param = ApiParameter(
            name="test",
            location=ParameterLocation.QUERY,
        )
        assert param.param_type == ParameterType.STRING
        assert param.required is False
        assert param.enum_values == []
        assert param.min_value is None
        assert param.max_value is None

    def test_full_parameter(self) -> None:
        param = ApiParameter(
            name="age",
            location=ParameterLocation.BODY,
            param_type=ParameterType.INTEGER,
            required=True,
            min_value=0,
            max_value=150,
            description="User age",
        )
        assert param.name == "age"
        assert param.location == ParameterLocation.BODY
        assert param.param_type == ParameterType.INTEGER
        assert param.required is True
        assert param.min_value == 0
        assert param.max_value == 150


class TestApiEndpoint:
    def test_endpoint_creation(self, simple_get_endpoint: ApiEndpoint) -> None:
        assert simple_get_endpoint.path == "/items"
        assert simple_get_endpoint.method == HttpMethod.GET
        assert len(simple_get_endpoint.parameters) == 2

    def test_endpoint_defaults(self) -> None:
        ep = ApiEndpoint(path="/test", method=HttpMethod.POST)
        assert ep.parameters == []
        assert ep.response_codes == []
        assert ep.content_type == "application/json"


class TestTestSuiteResult:
    def test_failure_rate_zero_tests(self) -> None:
        suite = TestSuiteResult()
        assert suite.failure_rate == 0.0

    def test_pass_rate_zero_tests(self) -> None:
        suite = TestSuiteResult()
        assert suite.pass_rate == 0.0

    def test_failure_rate_calculation(self) -> None:
        suite = TestSuiteResult(
            total_tests=10,
            passed=6,
            failed=3,
            errors=1,
        )
        assert suite.failure_rate == 40.0

    def test_pass_rate_calculation(self) -> None:
        suite = TestSuiteResult(
            total_tests=10,
            passed=8,
            failed=1,
            errors=1,
        )
        assert suite.pass_rate == 80.0


class TestChaosTestCase:
    def test_auto_id_generation(self) -> None:
        ep = ApiEndpoint(path="/test", method=HttpMethod.GET)
        tc1 = ChaosTestCase(
            endpoint=ep,
            strategy=ChaosStrategy.BOUNDARY_VALUES,
            description="Test 1",
        )
        tc2 = ChaosTestCase(
            endpoint=ep,
            strategy=ChaosStrategy.BOUNDARY_VALUES,
            description="Test 2",
        )
        assert tc1.id != tc2.id
        assert len(tc1.id) == 12
