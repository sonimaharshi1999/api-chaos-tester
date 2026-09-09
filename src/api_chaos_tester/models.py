# API Chaos Tester - Intelligent API Fuzz Testing
# Author: Maharshi Soni | License: MIT
"""
Domain models for API Chaos Tester using Pydantic v2.
Defines the data structures for API endpoints, parameters, test cases,
and test results used throughout the application.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class HttpMethod(str, Enum):
    """Supported HTTP methods."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class ParameterLocation(str, Enum):
    """Where a parameter is sent in the HTTP request."""

    QUERY = "query"
    PATH = "path"
    HEADER = "header"
    BODY = "body"


class ParameterType(str, Enum):
    """Supported parameter types for chaos generation."""

    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


class ChaosStrategy(str, Enum):
    """Available chaos testing strategies."""

    BOUNDARY_VALUES = "boundary_values"
    TYPE_CONFUSION = "type_confusion"
    NULL_INJECTION = "null_injection"
    UNICODE_STRESS = "unicode_stress"
    SQL_INJECTION = "sql_injection"
    OVERFLOW = "overflow"
    EMPTY_VALUES = "empty_values"
    SPECIAL_CHARACTERS = "special_characters"
    FORMAT_VIOLATION = "format_violation"


class TestStatus(str, Enum):
    """Status of a test case execution."""

    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


class ApiParameter(BaseModel):
    """Represents a single API parameter with its metadata."""

    name: str
    location: ParameterLocation
    param_type: ParameterType = ParameterType.STRING
    required: bool = False
    description: str = ""
    default: Any = None
    enum_values: list[str] = Field(default_factory=list)
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    format: Optional[str] = None  # e.g., "email", "date-time", "uuid"


class ApiEndpoint(BaseModel):
    """Represents an API endpoint parsed from an OpenAPI spec."""

    path: str
    method: HttpMethod
    operation_id: Optional[str] = None
    summary: str = ""
    description: str = ""
    parameters: list[ApiParameter] = Field(default_factory=list)
    request_body_schema: Optional[dict[str, Any]] = None
    response_codes: list[int] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    content_type: str = "application/json"


class ChaosTestCase(BaseModel):
    """A generated chaos test case for an endpoint."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    endpoint: ApiEndpoint
    strategy: ChaosStrategy
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    body: Optional[Any] = None
    expected_behavior: str = ""
    failure_probability: float = 0.0  # ML-predicted probability of finding a bug


class TestResult(BaseModel):
    """Result of executing a single chaos test case."""

    test_case: ChaosTestCase
    status: TestStatus
    status_code: Optional[int] = None
    response_body: Optional[str] = None
    response_time_ms: float = 0.0
    error_message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    reproduction_curl: str = ""


class TestSuiteResult(BaseModel):
    """Aggregated results from a full test suite run."""

    api_name: str = "Unknown API"
    base_url: str = ""
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    timeouts: int = 0
    results: list[TestResult] = Field(default_factory=list)
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0

    @property
    def failure_rate(self) -> float:
        """Calculate the failure rate as a percentage."""
        if self.total_tests == 0:
            return 0.0
        return ((self.failed + self.errors) / self.total_tests) * 100

    @property
    def pass_rate(self) -> float:
        """Calculate the pass rate as a percentage."""
        if self.total_tests == 0:
            return 0.0
        return (self.passed / self.total_tests) * 100
