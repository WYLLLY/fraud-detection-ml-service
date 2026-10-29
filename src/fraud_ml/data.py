"""Synthetic observations and stratified, immutable row-identity partitions."""

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import cast

import numpy as np
from numpy.typing import NDArray
from sklearn.model_selection import train_test_split as _split  # pyright: ignore[reportMissingTypeStubs, reportUnknownVariableType]

from fraud_ml.domain import SCALES, validate_features

# sklearn returns two lists for a single list input; keep this cast at the boundary.
train_test_split = cast(Callable[..., tuple[list[int], list[int]]], _split)


__all__ = [
    "SCALES",
    "validate_features",
    "Observation",
    "GeneratedData",
    "Partitions",
    "generate",
    "split",
    "select_rows",
    "feature_rows",
    "labels",
    "probability",
]


@dataclass(frozen=True)
class Observation:
    row_id: int
    amount_minor: int
    currency: str
    label: int


@dataclass(frozen=True)
class GeneratedData:
    observations: tuple[Observation, ...]
    probabilities: tuple[float, ...]


@dataclass(frozen=True)
class Partitions:
    train: tuple[int, ...]
    validation: tuple[int, ...]
    test: tuple[int, ...]


def probability(amount: int, currency: str) -> float:
    validate_features({"amount_minor": amount, "currency": currency})
    x = math.log(amount / SCALES[currency])
    return (
        0.01
        + 0.15 / (1 + math.exp(-2 * (x - 1.5)))
        + 0.04 * math.exp(-0.5 * ((x - 0.2) / 0.35) ** 2)
    )


def generate(samples: int = 60000, seed: int = 42) -> GeneratedData:
    if type(samples) is not int or samples < 1:
        raise ValueError("samples must be positive")
    rng = np.random.default_rng(seed)
    currencies = tuple(SCALES)
    observations: list[Observation] = []
    probabilities: list[float] = []
    for row_id in range(samples):
        currency = currencies[int(rng.integers(3))]
        while True:
            u = float(rng.normal(0, 1.1))
            if math.log(0.05) <= u <= math.log(50):
                break
        scale = SCALES[currency]
        amount = min(scale * 50, max(scale // 20, round(scale * math.exp(u))))
        p = probability(amount, currency)
        observations.append(Observation(row_id, amount, currency, int(rng.binomial(1, p))))
        probabilities.append(p)
    return GeneratedData(tuple(observations), tuple(probabilities))


def split(
    observations: Sequence[Observation], seed: int = 43, minimum_positives: int = 50
) -> Partitions:
    ids = [r.row_id for r in observations]
    if len(set(ids)) != len(ids) or not ids:
        raise ValueError("Row IDs must be unique and nonempty")
    if any(r.label not in (0, 1) for r in observations):
        raise ValueError("Labels must be binary")

    # sklearn returns untyped lists; normalize at this library boundary.
    train_ids, remainder = train_test_split(
        ids, test_size=0.3, random_state=seed, stratify=[r.label for r in observations]
    )
    by_id = {r.row_id: r for r in observations}
    val_ids, test_ids = train_test_split(
        remainder,
        test_size=0.5,
        random_state=seed,
        stratify=[by_id[int(i)].label for i in remainder],
    )
    result = Partitions(
        tuple(int(i) for i in train_ids),
        tuple(int(i) for i in val_ids),
        tuple(int(i) for i in test_ids),
    )
    for group in (result.train, result.validation, result.test):
        ys = [by_id[i].label for i in group]
        if set(ys) != {0, 1} or sum(ys) < minimum_positives:
            raise ValueError("Insufficient class support in partition")
    return result


def select_rows(observations: Sequence[Observation], ids: Sequence[int]) -> tuple[Observation, ...]:
    by_id = {r.row_id: r for r in observations}
    return tuple(by_id[i] for i in ids)


def feature_rows(observations: Sequence[Observation]) -> list[dict[str, object]]:
    return [{"amount_minor": r.amount_minor, "currency": r.currency} for r in observations]


def labels(observations: Sequence[Observation]) -> NDArray[np.int64]:
    return np.asarray([r.label for r in observations], dtype=np.int64)
