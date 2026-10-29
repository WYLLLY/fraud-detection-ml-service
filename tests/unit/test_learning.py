import copy

import numpy as np
import pytest
import torch

from fraud_ml.evaluation import choose_candidate, metrics, reliability, threshold_for
from fraud_ml.networks import MLP
from fraud_ml.training import TrainingConfig, predict_torch, train_torch


def fixture() -> tuple[
    np.ndarray[tuple[int, ...], np.dtype[np.float64]],
    np.ndarray[tuple[int, ...], np.dtype[np.int64]],
]:
    rng = np.random.default_rng(4)
    x = rng.normal(size=(256, 4))
    y = (x[:, 0] > 0).astype(np.int64)
    return x, y


def test_training_updates_weights_and_saved_checkpoint_is_not_a_live_alias() -> None:
    x, y = fixture()
    torch.manual_seed(44)  # pyright: ignore[reportUnknownMemberType]
    initial = copy.deepcopy(MLP().state_dict())
    result = train_torch(x, y, x, y, TrainingConfig(epochs=8, patience=5))
    assert any(not torch.equal(initial[k], v) for k, v in result.model.state_dict().items())
    assert result.best_epoch == int(np.argmax(result.history))
    for k, v in result.model.state_dict().items():
        torch.testing.assert_close(v, result.best_state[k])
    saved = copy.deepcopy(result.best_state)
    with torch.no_grad():
        next(result.model.parameters()).add_(1)
    for k in saved:
        torch.testing.assert_close(saved[k], result.best_state[k])


def test_prediction_is_finite_deterministic_and_does_not_update_parameters() -> None:
    x, y = fixture()
    config = TrainingConfig(epochs=3)
    first = train_torch(x, y, x, y, config)
    second = train_torch(x, y, x, y, config)
    before = copy.deepcopy(first.model.state_dict())
    p = predict_torch(first.model, x)
    assert p.shape == (len(y),) and np.isfinite(p).all()
    np.testing.assert_array_equal(p, predict_torch(second.model, x))
    for k in before:
        torch.testing.assert_close(before[k], first.model.state_dict()[k])


def test_loss_contract_rejects_broadcastable_targets_and_nonfinite_inputs() -> None:
    x, y = fixture()
    with pytest.raises(ValueError):
        train_torch(x, y.reshape(-1, 1), x, y, TrainingConfig(epochs=1))
    x[0, 0] = np.nan
    with pytest.raises(ValueError):
        train_torch(x, y, x, y, TrainingConfig(epochs=1))


def test_known_metrics_and_thresholds() -> None:
    y = np.array([0, 0, 1, 1], dtype=np.int64)
    p = np.array([0.1, 0.2, 0.8, 0.9])
    m = metrics(y, p, 0.5)
    assert m["ap"] == 1 and m["precision"] == 1 and m["recall"] == 1
    assert m["brier"] == pytest.approx(0.025)
    assert m["confusion"] == [[2, 0], [0, 2]]
    assert threshold_for(y, p) == 0.8
    assert choose_candidate(0.1, 0.11) == "logistic"
    assert choose_candidate(0.1, 0.110001) == "torch"
    tied = np.array([0.5] * 4)
    assert metrics(y, tied)["ap"] == 0.5
    bins = reliability(y, tied)
    assert len(bins) == 1 and bins[0]["count"] == 4
    assert bins[0]["observed"] == 0.5


def test_undefined_metrics_are_explicit_and_invalid_scores_rejected() -> None:
    y = np.array([0, 0], dtype=np.int64)
    m = metrics(y, np.array([0.1, 0.2]), 0.5)
    assert m["precision"] is None and m["recall"] is None and m["ap"] is None
    assert m["undefined"]
    for p in (np.array([np.nan, 0.5]), np.array([-1.0, 2.0])):
        with pytest.raises(ValueError):
            metrics(y, p)


def test_all_positive_average_precision_is_defined() -> None:
    result = metrics(np.array([1, 1], dtype=np.int64), np.array([0.2, 0.8]))
    assert result["ap"] == 1.0
    assert result["pr_auc_trapezoidal"] == 1.0
