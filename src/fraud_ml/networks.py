"""Inference-safe CPU neural network architecture."""

import numpy as np
import torch
from numpy.typing import NDArray
from torch import nn


class MLP(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(4, 16), nn.ReLU(), nn.Linear(16, 8), nn.ReLU(), nn.Linear(8, 1)
        )

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.layers(inputs).squeeze(-1)


def predict_torch(model: MLP, inputs: NDArray[np.float64]) -> NDArray[np.float64]:
    if inputs.ndim != 2 or inputs.shape[1] != 4 or not np.isfinite(inputs).all():
        raise ValueError("Expected finite four-column features")
    model.eval()
    with torch.inference_mode():
        p = torch.sigmoid(model(torch.tensor(inputs, dtype=torch.float32)))
    return np.asarray(p.numpy(), dtype=np.float64)
