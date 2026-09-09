# API Chaos Tester - Intelligent API Fuzz Testing
# Author: Maharshi Soni | License: MIT
"""
ML-based failure predictor.
Uses scikit-learn to predict which parameter/strategy combinations
are most likely to uncover bugs, based on historical test results
and heuristic feature engineering.
"""

from __future__ import annotations

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import LabelEncoder

from api_chaos_tester.models import (
    ApiParameter,
    ChaosStrategy,
    ChaosTestCase,
    ParameterType,
    TestResult,
    TestStatus,
)


# Heuristic weights: how likely a (param_type, strategy) combo is to find a bug.
# Based on common patterns from real-world API testing.
_HEURISTIC_SCORES: dict[tuple[ParameterType, ChaosStrategy], float] = {
    # Strings are most vulnerable to injection attacks
    (ParameterType.STRING, ChaosStrategy.SQL_INJECTION): 0.8,
    (ParameterType.STRING, ChaosStrategy.SPECIAL_CHARACTERS): 0.75,
    (ParameterType.STRING, ChaosStrategy.UNICODE_STRESS): 0.65,
    (ParameterType.STRING, ChaosStrategy.NULL_INJECTION): 0.6,
    (ParameterType.STRING, ChaosStrategy.BOUNDARY_VALUES): 0.55,
    (ParameterType.STRING, ChaosStrategy.TYPE_CONFUSION): 0.5,
    # Integers are vulnerable to boundary and type confusion
    (ParameterType.INTEGER, ChaosStrategy.BOUNDARY_VALUES): 0.7,
    (ParameterType.INTEGER, ChaosStrategy.TYPE_CONFUSION): 0.65,
    (ParameterType.INTEGER, ChaosStrategy.OVERFLOW): 0.6,
    (ParameterType.INTEGER, ChaosStrategy.NULL_INJECTION): 0.5,
    # Numbers similar to integers
    (ParameterType.NUMBER, ChaosStrategy.BOUNDARY_VALUES): 0.65,
    (ParameterType.NUMBER, ChaosStrategy.TYPE_CONFUSION): 0.6,
    (ParameterType.NUMBER, ChaosStrategy.OVERFLOW): 0.55,
    # Objects/Arrays are overflow-prone
    (ParameterType.OBJECT, ChaosStrategy.OVERFLOW): 0.7,
    (ParameterType.OBJECT, ChaosStrategy.TYPE_CONFUSION): 0.6,
    (ParameterType.ARRAY, ChaosStrategy.OVERFLOW): 0.65,
    (ParameterType.ARRAY, ChaosStrategy.BOUNDARY_VALUES): 0.6,
    # Booleans are less commonly broken
    (ParameterType.BOOLEAN, ChaosStrategy.TYPE_CONFUSION): 0.45,
    (ParameterType.BOOLEAN, ChaosStrategy.NULL_INJECTION): 0.4,
}

_DEFAULT_HEURISTIC = 0.3


def _param_feature_vector(param: ApiParameter, strategy: ChaosStrategy) -> list[float]:
    """
    Convert a parameter + strategy pair into a numeric feature vector for ML.

    Features:
    - param_type encoded as int (0-5)
    - strategy encoded as int (0-8)
    - is_required (0/1)
    - has_constraints (0/1) - min/max/pattern
    - has_enum (0/1)
    - has_format (0/1)
    """
    type_map = {t: i for i, t in enumerate(ParameterType)}
    strat_map = {s: i for i, s in enumerate(ChaosStrategy)}

    has_constraints = int(
        param.min_value is not None
        or param.max_value is not None
        or param.min_length is not None
        or param.max_length is not None
        or param.pattern is not None
    )

    return [
        type_map.get(param.param_type, 0),
        strat_map.get(strategy, 0),
        int(param.required),
        has_constraints,
        int(len(param.enum_values) > 0),
        int(param.format is not None),
    ]


class FailurePredictor:
    """
    Predicts the probability that a chaos test case will uncover a bug.

    Uses heuristic scoring when no historical data is available, and
    switches to an ML model once enough test results are collected.
    """

    _MIN_SAMPLES_FOR_ML = 30

    def __init__(self) -> None:
        self._model: GradientBoostingClassifier | None = None
        self._training_X: list[list[float]] = []
        self._training_y: list[int] = []
        self._is_trained: bool = False

    def predict(self, test_case: ChaosTestCase) -> float:
        """
        Predict the failure probability for a test case.

        Returns a float between 0.0 and 1.0 indicating how likely
        this test is to find a bug.
        """
        if self._is_trained and self._model is not None:
            return self._predict_ml(test_case)
        return self._predict_heuristic(test_case)

    def score_and_sort(
        self, test_cases: list[ChaosTestCase]
    ) -> list[ChaosTestCase]:
        """
        Score all test cases and sort by descending failure probability.
        This prioritizes the tests most likely to find bugs.
        """
        for tc in test_cases:
            tc.failure_probability = self.predict(tc)
        return sorted(test_cases, key=lambda t: t.failure_probability, reverse=True)

    def learn(self, results: list[TestResult]) -> None:
        """
        Ingest historical test results to improve future predictions.
        Retrains the ML model if enough samples are available.
        """
        for result in results:
            tc = result.test_case
            for param in tc.endpoint.parameters:
                features = _param_feature_vector(param, tc.strategy)
                # Label: 1 if the test found something interesting (not passed)
                label = 1 if result.status in (
                    TestStatus.FAILED, TestStatus.ERROR
                ) else 0
                self._training_X.append(features)
                self._training_y.append(label)

        if len(self._training_X) >= self._MIN_SAMPLES_FOR_ML:
            self._train_model()

    def _predict_heuristic(self, test_case: ChaosTestCase) -> float:
        """Use the heuristic scoring table when no ML model is available."""
        scores: list[float] = []
        for param in test_case.endpoint.parameters:
            key = (param.param_type, test_case.strategy)
            score = _HEURISTIC_SCORES.get(key, _DEFAULT_HEURISTIC)

            # Boost score for required params (more likely to cause real issues)
            if param.required:
                score = min(score * 1.15, 1.0)

            # Boost score for params with constraints (more validation to break)
            if param.min_value is not None or param.max_value is not None:
                score = min(score * 1.1, 1.0)

            scores.append(score)

        return max(scores) if scores else _DEFAULT_HEURISTIC

    def _predict_ml(self, test_case: ChaosTestCase) -> float:
        """Use the trained ML model for predictions."""
        if not self._model or not test_case.endpoint.parameters:
            return _DEFAULT_HEURISTIC

        probs: list[float] = []
        for param in test_case.endpoint.parameters:
            features = _param_feature_vector(param, test_case.strategy)
            X = np.array([features])
            prob = self._model.predict_proba(X)[0][1]  # Probability of class 1
            probs.append(float(prob))

        return max(probs) if probs else _DEFAULT_HEURISTIC

    def _train_model(self) -> None:
        """Train the gradient boosting model on collected data."""
        X = np.array(self._training_X)
        y = np.array(self._training_y)

        # Need at least two classes to train
        if len(set(y)) < 2:
            return

        self._model = GradientBoostingClassifier(
            n_estimators=50,
            max_depth=3,
            learning_rate=0.1,
            random_state=42,
        )
        self._model.fit(X, y)
        self._is_trained = True

    @property
    def is_ml_active(self) -> bool:
        """Whether the ML model is trained and active."""
        return self._is_trained
