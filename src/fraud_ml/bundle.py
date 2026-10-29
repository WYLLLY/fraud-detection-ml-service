"""Trusted local bundle loading; verify all metadata before deserialization."""

import importlib.metadata
import math
import platform
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

import numpy as np
import torch
from numpy.typing import NDArray

from fraud_ml.artifact_io import identity, read_json, verify_files
from fraud_ml.features import DOMAINS, FEATURE_ORDER, Preprocessor
from fraud_ml.library_io import load_local
from fraud_ml.models import LogisticScorer, Scorer, TorchScorer
from fraud_ml.networks import MLP


class Bundle:
    def __init__(
        self, preprocessor: Preprocessor, scorer: Scorer, threshold: float, version: str
    ) -> None:
        self.preprocessor, self.scorer = preprocessor, scorer
        self.threshold, self.version = threshold, version

    def predict(self, rows: Sequence[Mapping[str, object]]) -> NDArray[np.float64]:
        p = self.scorer.scores(self.preprocessor.transform(rows))
        if p.shape != (len(rows),) or not np.isfinite(p).all() or np.any((p < 0) | (p > 1)):
            raise ValueError("Invalid model probabilities")
        return p


def load_bundle(directory: Path) -> Bundle:
    """Only call on a trusted local release directory; checksums are not signatures."""
    manifest = read_json(directory / "manifest.json")
    kind = manifest.get("kind")
    threshold = manifest.get("threshold")
    version = manifest.pop("version", None)
    if (
        version != identity(manifest)
        or kind not in ("logistic", "torch")
        or not isinstance(threshold, (int, float))
        or isinstance(threshold, bool)
        or not math.isfinite(threshold)
        or not 0 <= threshold <= 1
    ):
        raise ValueError("Invalid bundle metadata or identity")
    if (
        manifest.get("feature_order") != list(FEATURE_ORDER)
        or manifest.get("domains") != {k: list(v) for k, v in DOMAINS.items()}
        or manifest.get("schema") != "synthetic-risk-v1"
    ):
        raise ValueError("Incompatible bundle schema")
    expected_files = {"preprocessor.joblib", "model.joblib" if kind == "logistic" else "model.pt"}
    if set(manifest.get("files", {})) != expected_files:
        raise ValueError("Invalid bundle file schema")
    environment = manifest.get("environment")
    if not isinstance(environment, dict):
        raise ValueError("Missing runtime compatibility metadata")
    runtime = cast(dict[str, object], environment)
    recorded_python = runtime.get("python")
    packages = runtime.get("packages")
    if (
        not isinstance(recorded_python, str)
        or recorded_python.split(".")[:2] != platform.python_version().split(".")[:2]
        or not isinstance(packages, dict)
    ):
        raise ValueError("Incompatible Python/runtime metadata")
    versions = cast(dict[str, object], packages)
    for name in ("numpy", "scikit-learn", "joblib", "torch"):
        expected, actual = versions.get(name), importlib.metadata.version(name)
        if not isinstance(expected, str):
            raise ValueError("Missing runtime package version")
        if name == "torch":
            expected, actual = expected.removesuffix("+cpu"), actual.removesuffix("+cpu")
        if expected != actual:
            raise ValueError(f"Incompatible runtime package {name}")
    verify_files(directory, manifest["files"])
    preprocessor = load_local(directory / "preprocessor.joblib")
    if (
        not isinstance(preprocessor, Preprocessor)
        or preprocessor.mean is None
        or preprocessor.scale is None
        or not math.isfinite(preprocessor.mean)
        or not math.isfinite(preprocessor.scale)
        or preprocessor.scale <= 0
    ):
        raise ValueError("Invalid fitted preprocessor")
    scorer: Scorer
    if kind == "logistic":
        model = load_local(directory / "model.joblib")
        if not isinstance(model, LogisticScorer):
            raise ValueError("Invalid sklearn model")
        scorer = model
    else:
        network = MLP()
        network.load_state_dict(
            torch.load(directory / "model.pt", weights_only=True, map_location="cpu"), strict=True
        )
        network.eval()
        scorer = TorchScorer(network)
    bundle = Bundle(preprocessor, scorer, float(threshold), str(version))
    bundle.predict([{"amount_minor": 1000, "currency": "EUR"}])
    return bundle
