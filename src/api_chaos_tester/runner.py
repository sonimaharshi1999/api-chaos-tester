# API Chaos Tester - Intelligent API Fuzz Testing
# Author: Maharshi Soni | License: MIT
"""
Test runner that executes chaos test cases against a target API.
Supports both real HTTP requests (via httpx) and mock-based testing
through a pluggable transport layer.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from typing import Any, Optional
from urllib.parse import urljoin

import httpx

from api_chaos_tester.models import (
    ChaosTestCase,
    HttpMethod,
    ParameterLocation,
    TestResult,
    TestStatus,
    TestSuiteResult,
)


def _build_curl_command(
    base_url: str,
    test_case: ChaosTestCase,
) -> str:
    """Generate a cURL command for reproducing a test case."""
    endpoint = test_case.endpoint
    url = urljoin(base_url, endpoint.path)

    # Replace path parameters
    for name, value in test_case.parameters.items():
        url = url.replace(f"{{{name}}}", str(value))

    parts = ["curl", "-X", endpoint.method.value]

    # Query params
    query_params = {
        name: value
        for name, value in test_case.parameters.items()
        if any(
            p.name == name and p.location == ParameterLocation.QUERY
            for p in endpoint.parameters
        )
    }
    if query_params:
        qs = "&".join(f"{k}={v}" for k, v in query_params.items())
        url = f"{url}?{qs}"

    parts.append(f"'{url}'")

    # Headers
    for hdr_name, hdr_value in test_case.headers.items():
        parts.append(f"-H '{hdr_name}: {hdr_value}'")

    # Body
    if test_case.body is not None:
        import json

        parts.append(f"-H 'Content-Type: {endpoint.content_type}'")
        parts.append(f"-d '{json.dumps(test_case.body)}'")

    return " \\\n  ".join(parts)


async def _execute_single_test(
    client: httpx.AsyncClient,
    base_url: str,
    test_case: ChaosTestCase,
    timeout: float = 10.0,
) -> TestResult:
    """Execute a single chaos test case and return the result."""
    endpoint = test_case.endpoint
    url = urljoin(base_url, endpoint.path)

    # Replace path parameters
    for param in endpoint.parameters:
        if param.location == ParameterLocation.PATH and param.name in test_case.parameters:
            url = url.replace(
                f"{{{param.name}}}", str(test_case.parameters[param.name])
            )

    # Build query params
    query_params: dict[str, Any] = {}
    for param in endpoint.parameters:
        if param.location == ParameterLocation.QUERY and param.name in test_case.parameters:
            query_params[param.name] = test_case.parameters[param.name]

    # Build headers
    headers = dict(test_case.headers)
    if test_case.body is not None:
        headers.setdefault("Content-Type", endpoint.content_type)

    curl_cmd = _build_curl_command(base_url, test_case)
    start_time = time.monotonic()

    try:
        response = await client.request(
            method=endpoint.method.value,
            url=url,
            params=query_params if query_params else None,
            json=test_case.body if test_case.body is not None else None,
            headers=headers if headers else None,
            timeout=timeout,
        )
        elapsed_ms = (time.monotonic() - start_time) * 1000

        # Determine status based on response
        status_code = response.status_code
        response_text = response.text[:2000]  # Truncate large responses

        if 500 <= status_code < 600:
            test_status = TestStatus.FAILED
        elif 400 <= status_code < 500:
            test_status = TestStatus.PASSED  # Expected rejection
        else:
            # 2xx/3xx with chaos input might indicate missing validation
            test_status = TestStatus.PASSED

        return TestResult(
            test_case=test_case,
            status=test_status,
            status_code=status_code,
            response_body=response_text,
            response_time_ms=elapsed_ms,
            reproduction_curl=curl_cmd,
        )

    except httpx.TimeoutException:
        elapsed_ms = (time.monotonic() - start_time) * 1000
        return TestResult(
            test_case=test_case,
            status=TestStatus.TIMEOUT,
            response_time_ms=elapsed_ms,
            error_message="Request timed out",
            reproduction_curl=curl_cmd,
        )
    except Exception as exc:
        elapsed_ms = (time.monotonic() - start_time) * 1000
        return TestResult(
            test_case=test_case,
            status=TestStatus.ERROR,
            response_time_ms=elapsed_ms,
            error_message=str(exc),
            reproduction_curl=curl_cmd,
        )


async def run_tests(
    test_cases: list[ChaosTestCase],
    base_url: str,
    concurrency: int = 5,
    timeout: float = 10.0,
    client: httpx.AsyncClient | None = None,
    api_name: str = "Unknown API",
    progress_callback: Any = None,
) -> TestSuiteResult:
    """
    Run a batch of chaos test cases against the target API.

    Args:
        test_cases: The test cases to execute.
        base_url: Base URL of the target API.
        concurrency: Maximum number of concurrent requests.
        timeout: Request timeout in seconds.
        client: Optional pre-configured httpx.AsyncClient (for mocking).
        api_name: Name of the API under test.
        progress_callback: Optional callable(completed, total) for progress.

    Returns:
        Aggregated test suite results.
    """
    suite = TestSuiteResult(
        api_name=api_name,
        base_url=base_url,
        total_tests=len(test_cases),
        start_time=datetime.now(),
    )

    if not test_cases:
        suite.end_time = datetime.now()
        return suite

    own_client = client is None
    if own_client:
        client = httpx.AsyncClient()

    semaphore = asyncio.Semaphore(concurrency)
    completed = 0

    async def bounded_execute(tc: ChaosTestCase) -> TestResult:
        nonlocal completed
        async with semaphore:
            result = await _execute_single_test(client, base_url, tc, timeout)  # type: ignore[arg-type]
            completed += 1
            if progress_callback:
                progress_callback(completed, len(test_cases))
            return result

    try:
        tasks = [bounded_execute(tc) for tc in test_cases]
        results = await asyncio.gather(*tasks)
    finally:
        if own_client:
            await client.aclose()  # type: ignore[union-attr]

    for result in results:
        suite.results.append(result)
        match result.status:
            case TestStatus.PASSED:
                suite.passed += 1
            case TestStatus.FAILED:
                suite.failed += 1
            case TestStatus.ERROR:
                suite.errors += 1
            case TestStatus.SKIPPED:
                suite.skipped += 1
            case TestStatus.TIMEOUT:
                suite.timeouts += 1

    suite.end_time = datetime.now()
    suite.duration_seconds = (suite.end_time - suite.start_time).total_seconds()

    return suite


def run_tests_sync(
    test_cases: list[ChaosTestCase],
    base_url: str,
    concurrency: int = 5,
    timeout: float = 10.0,
    client: httpx.AsyncClient | None = None,
    api_name: str = "Unknown API",
    progress_callback: Any = None,
) -> TestSuiteResult:
    """Synchronous wrapper around run_tests for non-async contexts."""
    return asyncio.run(
        run_tests(
            test_cases=test_cases,
            base_url=base_url,
            concurrency=concurrency,
            timeout=timeout,
            client=client,
            api_name=api_name,
            progress_callback=progress_callback,
        )
    )
