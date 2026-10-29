import math

import numpy as np
import pytest

from fraud_ml.data import (
    SCALES,
    Observation,
    feature_rows,
    generate,
    probability,
    split,
    validate_features,
)
from fraud_ml.features import Preprocessor


def test_generator_is_seeded_bounded_and_oracle_is_separate() -> None:
    data = generate(6000)
    assert len(data.observations) == 6000
    assert data == generate(6000)
    assert data != generate(6000, 41)
    assert len({r.row_id for r in data.observations}) == 6000
    for row, p in zip(data.observations, data.probabilities, strict=True):
        assert type(row.amount_minor) is int
        assert 0.05 * SCALES[row.currency] <= row.amount_minor <= 50 * SCALES[row.currency]
        assert row.label in (0, 1)
        assert p == pytest.approx(probability(row.amount_minor, row.currency))
    assert 0.01 < np.mean([r.label for r in data.observations]) < 0.1
    assert set(feature_rows(data.observations)[0]) == {"amount_minor", "currency"}


def test_probability_is_the_documented_bernoulli_parameter() -> None:
    for currency, scale in SCALES.items():
        for amount in (scale, scale * 10):
            x = math.log(amount / scale)
            expected = (
                0.01
                + 0.15 / (1 + math.exp(-2 * (x - 1.5)))
                + 0.04 * math.exp(-0.5 * ((x - 0.2) / 0.35) ** 2)
            )
            assert probability(amount, currency) == pytest.approx(expected)


@pytest.mark.parametrize("bad", [True, 1.0, "1000", 0, -1, 10**13, None])
def test_invalid_amount_is_not_coerced(bad: object) -> None:
    with pytest.raises(ValueError):
        validate_features({"amount_minor": bad, "currency": "EUR"})


@pytest.mark.parametrize("extra", ["label", "p", "row_id", "state"])
def test_leakage_columns_are_rejected(extra: str) -> None:
    with pytest.raises(ValueError):
        Preprocessor().fit([{"amount_minor": 1000, "currency": "EUR", extra: 1}])


def test_currency_domains_and_strict_schema() -> None:
    for currency, scale in SCALES.items():
        assert validate_features({"amount_minor": int(scale * 0.05), "currency": currency}) == (
            int(scale * 0.05),
            currency,
        )
        for amount in (int(scale * 0.05) - 1, scale * 50 + 1):
            with pytest.raises(ValueError, match="outside_training_domain"):
                validate_features({"amount_minor": amount, "currency": currency})
    with pytest.raises(ValueError):
        validate_features({"amount_minor": 1000, "currency": "GBP"})
    with pytest.raises(ValueError):
        validate_features({"amount_minor": 1000})


def test_splits_are_frozen_disjoint_and_preserve_every_row() -> None:
    rows = generate(6000).observations
    parts = split(rows, minimum_positives=10)
    assert parts == split(rows, minimum_positives=10)
    assert (len(parts.train), len(parts.validation), len(parts.test)) == (4200, 900, 900)
    groups = [set(parts.train), set(parts.validation), set(parts.test)]
    assert not groups[0] & groups[1] and not groups[1] & groups[2] and not groups[0] & groups[2]
    assert groups[0].union(*groups[1:]) == {r.row_id for r in rows}
    with pytest.raises(ValueError):
        split(rows, minimum_positives=1000)
    with pytest.raises(ValueError):
        split((Observation(1, 1000, "EUR", 0),) * 10, minimum_positives=0)


def test_preprocessing_is_train_only_four_columns_and_fixed_currency_order() -> None:
    train = [{"amount_minor": 1000, "currency": "EUR"}, {"amount_minor": 10000, "currency": "USD"}]
    held_out = [{"amount_minor": 750000, "currency": "JPY"}]
    transform = Preprocessor().fit(train)
    before = transform.transform(train)
    assert before.shape == (2, 4)
    np.testing.assert_allclose(before[:, 0], [-1, 1])
    np.testing.assert_array_equal(before[:, 1:], [[1, 0, 0], [0, 1, 0]])
    assert transform.transform(held_out)[0, 0] > 1
    np.testing.assert_array_equal(transform.transform(train), before)
    with pytest.raises(ValueError, match="fitted"):
        Preprocessor().transform(train)
