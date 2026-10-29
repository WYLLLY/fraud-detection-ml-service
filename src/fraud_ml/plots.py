"""Standalone report figures, never loaded by inference."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import numpy as np
from matplotlib import pyplot as plt
from numpy.typing import NDArray

from fraud_ml.evaluation import precision_recall_curve, reliability


def plot_evaluation(
    labels: NDArray[np.int64], candidates: dict[str, NDArray[np.float64]], directory: Path
) -> None:
    fig, ax = plt.subplots()
    for name, scores in candidates.items():
        precision, recall, _ = precision_recall_curve(labels, scores)
        ax.plot(recall, precision, label=name)  # pyright: ignore[reportUnknownMemberType]
    ax.set(xlabel="Recall", ylabel="Precision", title="Synthetic held-out precision–recall")
    ax.legend()  # pyright: ignore[reportUnknownMemberType]
    fig.savefig(directory / "pr.png", dpi=150, bbox_inches="tight")  # pyright: ignore[reportUnknownMemberType]
    plt.close(fig)
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1], "--", color="gray")  # pyright: ignore[reportUnknownMemberType]
    for name, scores in candidates.items():
        bins = reliability(labels, scores)
        ax.plot([b["predicted"] for b in bins], [b["observed"] for b in bins], "o-", label=name)  # pyright: ignore[reportUnknownMemberType]
    ax.set(
        xlabel="Mean predicted probability",
        ylabel="Observed positive fraction",
        title="Synthetic held-out calibration (quantile groups)",
    )
    ax.legend()  # pyright: ignore[reportUnknownMemberType]
    fig.savefig(directory / "calibration.png", dpi=150, bbox_inches="tight")  # pyright: ignore[reportUnknownMemberType]
    plt.close(fig)
