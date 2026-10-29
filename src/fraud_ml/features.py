"""Closed-schema, train-fitted features; no generator/training imports."""

import math
from collections.abc import Mapping, Sequence

import numpy as np
from numpy.typing import NDArray

from fraud_ml.domain import DOMAINS, FEATURE_ORDER, validate_features

__all__ = ["DOMAINS", "FEATURE_ORDER", "Preprocessor", "checked_rows"]


def checked_rows(rows: Sequence[Mapping[str, object]]) -> NDArray[np.float64]:
    if not rows:
        raise ValueError("Feature rows must be nonempty")
    result: list[list[float]] = []
    for row in rows:
        amount, currency = validate_features(row)
        result.append([math.log1p(amount), *[float(currency == c) for c in DOMAINS]])
    return np.asarray(result, dtype=np.float64)


class Preprocessor:
    """Small serializable equivalent of a log/scaler plus fixed one-hot transform."""

    def __init__(self) -> None:
        self.mean: float | None = None
        self.scale: float | None = None

    def fit(self, rows: Sequence[Mapping[str, object]]) -> "Preprocessor":
        x = checked_rows(rows)
        self.mean = float(np.mean(x[:, 0]))
        self.scale = float(np.std(x[:, 0])) or 1.0
        return self

    def transform(self, rows: Sequence[Mapping[str, object]]) -> NDArray[np.float64]:
        if self.mean is None or self.scale is None:
            raise ValueError("Preprocessor must be fitted on train first")
        x = checked_rows(rows)
        x[:, 0] = (x[:, 0] - self.mean) / self.scale
        return x
