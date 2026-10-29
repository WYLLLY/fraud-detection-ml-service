"""Typed prediction adapters isolate third-party estimators from orchestration."""

from typing import Protocol, cast

import numpy as np
from numpy.typing import NDArray
from sklearn.linear_model import LogisticRegression  # pyright: ignore[reportMissingTypeStubs]

from fraud_ml.networks import MLP, predict_torch

Array = NDArray[np.float64]


class Estimator(Protocol):
    def fit(self, x: Array, y: NDArray[np.int64]) -> object: ...
    def predict_proba(self, x: Array) -> Array: ...


class Scorer(Protocol):
    def scores(self, x: Array) -> Array: ...


class LogisticScorer:
    def __init__(self) -> None:
        self.estimator = cast(Estimator, LogisticRegression(C=1, max_iter=1000))

    def fit(self, x: Array, y: NDArray[np.int64]) -> None:
        self.estimator.fit(x, y)

    def scores(self, x: Array) -> Array:
        return np.asarray(self.estimator.predict_proba(x)[:, 1], dtype=np.float64)


class TorchScorer:
    def __init__(self, model: MLP) -> None:
        self.model = model

    def scores(self, x: Array) -> Array:
        return predict_torch(self.model, x)
