# API Chaos Tester - Intelligent API Fuzz Testing
# Author: Maharshi Soni | License: MIT
"""Tests for the test runner using httpx mocking via respx."""

from __future__ import annotations

import asyncio

import httpx
import pytest
import respx

from api_chaos_tester.models import (
    ApiEndpoint,
    ApiParameter,
    ChaosStrategy,
    ChaosTestCase,
    HttpMethod,
    ParameterLocation,
    ParameterType,
    TestStatus,
)
from api_chaos_tester.runner import run_tests


def _make_chaos_case(
    path: str = "/items",
    method: HttpMethod = HttpMethod.GET,
    strategy: ChaosStrategy = ChaosStrategy.BOUNDARY_VALUES,
    params: dict | None = None,
    body: object = None,
) -> ChaosTestCase:
    """Helper to create a test case for runner tests."""
    return ChaosTestCase(
        endpoint=ApiEndpoint(
            path=path,
            method=method,
            parameters=[
                ApiParameter(
                    name="q",
                    location=ParameterLocation.QUERY,
                    param_type=ParameterType.STRING,
                ),
            ],
        ),
        strategy=strategy,
        description=f"Test {strategy.value}",
        parameters=params or {},
        body=body,
    )


class TestRunner:
    @pytest.mark.asyncio
    async def test_successful_request(self) -> None:
        with respx.mock:
            respx.get("http://test.local/items").mock(
                return_value=httpx.Response(200, json={"items": []})
            )

            async with httpx.AsyncClient() as client:
                suite = await run_tests(
                    test_cases=[_make_chaos_case()],
                    base_url="http://test.local",
                    client=client,
                )

            assert suite.total_tests == 1
            assert suite.passed == 1
            assert suite.results[0].status == TestStatus.PASSED
            assert suite.results[0].status_code == 200

    @pytest.mark.asyncio
    async def test_server_error_counts_as_failure(self) -> None:
        with respx.mock:
            respx.get("http://test.local/items").mock(
                return_value=httpx.Response(500, text="Internal Server Error")
            )

            async with httpx.AsyncClient() as client:
                suite = await run_tests(
                    test_cases=[_make_chaos_case()],
                    base_url="http://test.local",
                    client=client,
                )

            assert suite.failed == 1
            assert suite.results[0].status == TestStatus.FAILED
            assert suite.results[0].status_code == 500

    @pytest.mark.asyncio
    async def test_client_error_counts_as_pass(self) -> None:
        """A 4xx response to chaos input means the API correctly rejected it."""
        with respx.mock:
            respx.get("http://test.local/items").mock(
                return_value=httpx.Response(400, json={"error": "Bad request"})
            )

            async with httpx.AsyncClient() as client:
                suite = await run_tests(
                    test_cases=[_make_chaos_case()],
                    base_url="http://test.local",
                    client=client,
                )

            assert suite.passed == 1
            assert suite.results[0].status_code == 400

    @pytest.mark.asyncio
    async def test_connection_error(self) -> None:
        with respx.mock:
            respx.get("http://test.local/items").mock(
                side_effect=httpx.ConnectError("Connection refused")
            )

            async with httpx.AsyncClient() as client:
                suite = await run_tests(
                    test_cases=[_make_chaos_case()],
                    base_url="http://test.local",
                    client=client,
                )

            assert suite.errors == 1
            assert suite.results[0].status == TestStatus.ERROR
            assert "Connection refused" in (suite.results[0].error_message or "")

    @pytest.mark.asyncio
    async def test_multiple_concurrent_requests(self) -> None:
        with respx.mock:
            respx.get("http://test.local/items").mock(
                return_value=httpx.Response(200, json={})
            )

            cases = [_make_chaos_case() for _ in range(10)]
            async with httpx.AsyncClient() as client:
                suite = await run_tests(
                    test_cases=cases,
                    base_url="http://test.local",
                    concurrency=3,
                    client=client,
                )

            assert suite.total_tests == 10
            assert suite.passed == 10

    @pytest.mark.asyncio
    async def test_empty_test_cases(self) -> None:
        suite = await run_tests(
            test_cases=[],
            base_url="http://test.local",
        )
        assert suite.total_tests == 0
        assert suite.passed == 0

    @pytest.mark.asyncio
    async def test_reproduction_curl_generated(self) -> None:
        with respx.mock:
            respx.get("http://test.local/items").mock(
                return_value=httpx.Response(200, json={})
            )

            async with httpx.AsyncClient() as client:
                suite = await run_tests(
                    test_cases=[_make_chaos_case()],
                    base_url="http://test.local",
                    client=client,
                )

            assert "curl" in suite.results[0].reproduction_curl
            assert "GET" in suite.results[0].reproduction_curl

    @pytest.mark.asyncio
    async def test_post_with_body(self) -> None:
        with respx.mock:
            respx.post("http://test.local/items").mock(
                return_value=httpx.Response(201, json={"id": 1})
            )

            tc = ChaosTestCase(
                endpoint=ApiEndpoint(
                    path="/items",
                    method=HttpMethod.POST,
                    parameters=[
                        ApiParameter(
                            name="name",
                            location=ParameterLocation.BODY,
                            param_type=ParameterType.STRING,
                        ),
                    ],
                ),
                strategy=ChaosStrategy.NULL_INJECTION,
                description="Test null body",
                body={"name": None},
            )

            async with httpx.AsyncClient() as client:
                suite = await run_tests(
                    test_cases=[tc],
                    base_url="http://test.local",
                    client=client,
                )

            assert suite.total_tests == 1
            assert suite.results[0].status_code == 201
