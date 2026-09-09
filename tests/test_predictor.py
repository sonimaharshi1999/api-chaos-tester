# API Chaos Tester - Intelligent API Fuzz Testing
# Author: Maharshi Soni | License: MIT
"""Tests for the ML-based failure predictor."""

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
)
from api_chaos_tester.predictor import FailurePredictor


def _make_test_case(
    param_type: ParameterType,
    strategy: ChaosStrategy,
    required: bool = False,
) -> ChaosTestCase:
    """Helper to create a minimal test case."""
    return ChaosTestCase(
        endpoint=ApiEndpoint(
            path="/test",
            method=HttpMethod.GET,
            parameters=[
                ApiParameter(
                    name="param",
                    location=ParameterLocation.QUERY,
                    param_type=param_type,
                    required=required,
                )
            ],
        ),
        strategy=strategy,
        description="Test case",
    )


class TestFailurePredictor:
    def test_heuristic_prediction(self) -> None:
        predictor = FailurePredictor()
        tc = _make_test_case(ParameterType.STRING, ChaosStrategy.SQL_INJECTION)
        prob = predictor.predict(tc)
        assert 0.0 <= prob <= 1.0
        # SQL injection on strings should score high
        assert prob > 0.5

    def test_required_param_boost(self) -> None:
        predictor = FailurePredictor()
        tc_optional = _make_test_case(
            ParameterType.STRING, ChaosStrategy.NULL_INJECTION, required=False
        )
        tc_required = _make_test_case(
            ParameterType.STRING, ChaosStrategy.NULL_INJECTION, required=True
        )
        prob_opt = predictor.predict(tc_optional)
        prob_req = predictor.predict(tc_required)
        # Required params should score higher for null injection
        assert prob_req >= prob_opt

    def test_score_and_sort(self) -> None:
        predictor = FailurePredictor()
        cases = [
            _make_test_case(ParameterType.BOOLEAN, ChaosStrategy.NULL_INJECTION),
            _make_test_case(ParameterType.STRING, ChaosStrategy.SQL_INJECTION),
            _make_test_case(ParameterType.INTEGER, ChaosStrategy.BOUNDARY_VALUES),
        ]
        sorted_cases = predictor.score_and_sort(cases)
        # Should be sorted by descending probability
        probs = [tc.failure_probability for tc in sorted_cases]
        assert probs == sorted(probs, reverse=True)

    def test_ml_not_active_initially(self) -> None:
        predictor = FailurePredictor()
        assert predictor.is_ml_active is False

    def test_learn_with_insufficient_data(self) -> None:
        predictor = FailurePredictor()
        # Feed a small number of results -- not enough to train ML
        results = []
        for i in range(5):
            tc = _make_test_case(ParameterType.STRING, ChaosStrategy.BOUNDARY_VALUES)
            results.append(
                TestResult(
                    test_case=tc,
                    status=TestStatus.PASSED if i % 2 == 0 else TestStatus.FAILED,
                )
            )
        predictor.learn(results)
        assert predictor.is_ml_active is False

    def test_learn_activates_ml(self) -> None:
        predictor = FailurePredictor()
        results = []
        # Generate enough diverse samples to train
        for i in range(40):
            param_type = [ParameterType.STRING, ParameterType.INTEGER][i % 2]
            strategy = [ChaosStrategy.BOUNDARY_VALUES, ChaosStrategy.NULL_INJECTION][
                i % 2
            ]
            tc = _make_test_case(param_type, strategy)
            results.append(
                TestResult(
                    test_case=tc,
                    status=TestStatus.PASSED if i % 3 != 0 else TestStatus.FAILED,
                )
            )
        predictor.learn(results)
        assert predictor.is_ml_active is True

        # Prediction should still return a valid probability
        tc = _make_test_case(ParameterType.STRING, ChaosStrategy.BOUNDARY_VALUES)
        prob = predictor.predict(tc)
        assert 0.0 <= prob <= 1.0

    def test_predict_no_params_returns_default(self) -> None:
        predictor = FailurePredictor()
        tc = ChaosTestCase(
            endpoint=ApiEndpoint(path="/empty", method=HttpMethod.GET, parameters=[]),
            strategy=ChaosStrategy.BOUNDARY_VALUES,
            description="No params",
        )
        prob = predictor.predict(tc)
        assert prob == 0.3  # default heuristic
