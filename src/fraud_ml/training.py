"""CPU optimization consuming transformed train and validation only."""

import copy
import random
from dataclasses import dataclass

import numpy as np
import torch
from numpy.typing import NDArray
from torch import nn

from fraud_ml.evaluation import metrics
from fraud_ml.networks import MLP, predict_torch

__all__ = ["TrainingConfig", "TrainingResult", "train_torch", "predict_torch"]


@dataclass(frozen=True)
class TrainingConfig:
    epochs: int = 50
    patience: int = 5
    batch_size: int = 256
    learning_rate: float = 0.001
    training_seed: int = 44


@dataclass(frozen=True)
class TrainingResult:
    model: MLP
    best_epoch: int
    history: tuple[float, ...]
    best_state: dict[str, torch.Tensor]


def train_torch(
    train_x: NDArray[np.float64],
    train_y: NDArray[np.int64],
    val_x: NDArray[np.float64],
    val_y: NDArray[np.int64],
    config: TrainingConfig | None = None,
) -> TrainingResult:
    config = config or TrainingConfig()
    for x, y in ((train_x, train_y), (val_x, val_y)):
        if (
            x.ndim != 2
            or x.shape[1] != 4
            or y.shape != (len(x),)
            or not len(x)
            or not np.isfinite(x).all()
            or not np.isin(y, [0, 1]).all()
        ):
            raise ValueError("Expected aligned finite features and one-dimensional binary targets")
        if len(np.unique(y)) != 2:
            raise ValueError("Both classes required for training/validation")
    if (
        min(config.epochs, config.patience, config.batch_size) < 1
        or not np.isfinite(config.learning_rate)
        or config.learning_rate <= 0
    ):
        raise ValueError("Invalid training configuration")
    random.seed(config.training_seed)
    np.random.seed(config.training_seed)
    torch.manual_seed(config.training_seed)  # pyright: ignore[reportUnknownMemberType]
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    model = MLP()
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    criterion = nn.BCEWithLogitsLoss()
    x = torch.tensor(train_x, dtype=torch.float32)
    y = torch.tensor(train_y, dtype=torch.float32)
    history: list[float] = []
    best_ap, best_epoch, stale = -1.0, 0, 0
    best_state = copy.deepcopy(model.state_dict())
    generator = torch.Generator().manual_seed(config.training_seed)
    for epoch in range(config.epochs):
        model.train()
        order = torch.randperm(len(y), generator=generator)
        for offset in range(0, len(y), config.batch_size):
            indices = order[offset : offset + config.batch_size]
            optimizer.zero_grad(set_to_none=True)
            loss = criterion(model(x[indices]), y[indices])
            if not bool(torch.isfinite(loss)):
                raise ValueError("Nonfinite loss")
            loss.backward()
            optimizer.step()  # pyright: ignore[reportUnknownMemberType]
        score = metrics(val_y, predict_torch(model, val_x))["ap"]
        if not isinstance(score, float) or not np.isfinite(score):
            raise ValueError("Undefined validation AP")
        history.append(score)
        if score > best_ap:
            best_ap, best_epoch, stale = score, epoch, 0
            best_state = copy.deepcopy(model.state_dict())
        else:
            stale += 1
        if stale >= config.patience:
            break
    model.load_state_dict(best_state, strict=True)
    model.eval()
    return TrainingResult(model, best_epoch, tuple(history), dict(best_state))
