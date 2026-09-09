# API Chaos Tester - Intelligent API Fuzz Testing
# Author: Maharshi Soni | License: MIT
"""
Base class for all chaos testing strategies.
Each concrete strategy inherits from BaseStrategy and implements
the `generate` method to produce ChaosTestCase instances.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from api_chaos_tester.models import ApiEndpoint, ChaosStrategy, ChaosTestCase


class BaseStrategy(ABC):
    """Abstract base class for chaos test generation strategies."""

    strategy_type: ChaosStrategy

    @abstractmethod
    def generate(self, endpoint: ApiEndpoint) -> list[ChaosTestCase]:
        """
        Generate chaos test cases for the given endpoint.

        Args:
            endpoint: The API endpoint to generate tests for.

        Returns:
            A list of chaos test cases targeting this endpoint.
        """
        ...

    def _make_case(
        self,
        endpoint: ApiEndpoint,
        description: str,
        parameters: dict | None = None,
        body: object = None,
        headers: dict[str, str] | None = None,
        expected_behavior: str = "",
    ) -> ChaosTestCase:
        """Helper to build a ChaosTestCase with common defaults."""
        return ChaosTestCase(
            endpoint=endpoint,
            strategy=self.strategy_type,
            description=description,
            parameters=parameters or {},
            body=body,
            headers=headers or {},
            expected_behavior=expected_behavior,
        )
