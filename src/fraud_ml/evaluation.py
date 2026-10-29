"""Pure, JSON-safe metrics and validation-only candidate decisions."""

import math
from collections.abc import Callable
from typing import cast

import numpy as np
from numpy.typing import NDArray
from sklearn.metrics import average_precision_score as _ap  # pyright: ignore[reportMissingTypeStubs, reportUnknownVariableType]
from sklearn.metrics import precision_recall_curve as _pr  # pyright: ignore[reportMissingTypeStubs, reportUnknownVariableType]

average_precision_score = cast(Callable[[NDArray[np.int64], NDArray[np.float64]], float], _ap)
precision_recall_curve = cast(
    Callable[
        [NDArray[np.int64], NDArray[np.float64]],
        tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]],
    ],
    _pr,
)


def checked(labels: NDArray[np.int64], scores: NDArray[np.float64]) -> None:
    if labels.ndim != 1 or scores.shape != labels.shape or len(labels) == 0:
        raise ValueError("Expected aligned nonempty one-dimensional arrays")
    if (
        not np.isin(labels, [0, 1]).all()
        or not np.isfinite(scores).all()
        or np.any((scores < 0) | (scores > 1))
    ):
        raise ValueError("Invalid labels or probability scores")


def threshold_for(labels: NDArray[np.int64], scores: NDArray[np.float64]) -> float:
    checked(labels, scores)
    best = (-1.0, -1.0, -1.0)
    # Evaluate unique thresholds once in O(n log n), preserving score >= threshold.
    order = np.argsort(-scores, kind="stable")
    sorted_scores, ys = scores[order], labels[order]
    tp = np.cumsum(ys)
    total = int(np.sum(labels))
    for i in np.flatnonzero(np.r_[sorted_scores[1:] != sorted_scores[:-1], True]):
        positive = int(i) + 1
        true_positive = int(tp[i])
        precision = true_positive / positive
        f1 = 2 * true_positive / (positive + total) if positive + total else 0.0
        best = max(best, (f1, precision, float(sorted_scores[i])))
    return best[2]


def choose_candidate(logistic_ap: float, torch_ap: float) -> str:
    if not all(math.isfinite(p) and 0 <= p <= 1 for p in (logistic_ap, torch_ap)):
        raise ValueError("Invalid validation AP")
    return "torch" if torch_ap > logistic_ap + 0.01 else "logistic"


def reliability(
    labels: NDArray[np.int64], scores: NDArray[np.float64]
) -> list[dict[str, float | int]]:
    checked(labels, scores)
    edges = np.unique(np.quantile(scores, np.linspace(0, 1, 11)))
    groups = np.searchsorted(edges[1:-1], scores, side="right")
    return [
        {
            "count": int(np.count_nonzero(groups == k)),
            "predicted": float(np.mean(scores[groups == k])),
            "observed": float(np.mean(labels[groups == k])),
        }
        for k in np.unique(groups)
    ]


def metrics(
    labels: NDArray[np.int64], scores: NDArray[np.float64], threshold: float = 0.5
) -> dict[str, object]:
    checked(labels, scores)
    if not math.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("Invalid threshold")
    predicted = scores >= threshold
    tp = int(np.count_nonzero(predicted & (labels == 1)))
    fp = int(np.count_nonzero(predicted & (labels == 0)))
    fn = int(np.count_nonzero(~predicted & (labels == 1)))
    tn = int(np.count_nonzero(~predicted & (labels == 0)))
    has_positives = bool(np.any(labels == 1))
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    if has_positives:
        pr, re, _ = precision_recall_curve(labels, scores)
        ap = float(average_precision_score(labels, scores))
        pr_auc = float(np.trapezoid(pr[::-1], re[::-1]))
    else:
        ap, pr_auc = None, None
    clipped = np.clip(scores, np.finfo(np.float64).eps, 1 - np.finfo(np.float64).eps)
    return {
        "samples": len(labels),
        "positives": int(np.sum(labels)),
        "prevalence": float(np.mean(labels)),
        "precision": precision,
        "recall": recall,
        "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
        "confusion": [[tn, fp], [fn, tp]],
        "ap": ap,
        "pr_auc_trapezoidal": pr_auc,
        "brier": float(np.mean((labels - scores) ** 2)),
        "log_loss": float(-np.mean(labels * np.log(clipped) + (1 - labels) * np.log(1 - clipped))),
        "reliability": reliability(labels, scores),
        "threshold": threshold,
        "undefined": [
            name
            for name, condition in [
                ("precision", precision is None),
                ("recall", recall is None),
                ("ranking_no_positives", not has_positives),
            ]
            if condition
        ],
    }
