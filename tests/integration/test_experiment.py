import json
import subprocess
import sys
from pathlib import Path
from typing import cast

import numpy as np
import pytest

from fraud_ml.bundle import load_bundle
from fraud_ml.experiment import (
    ExperimentConfig,
    evaluate_experiment,
    generate_experiment,
    train_experiment,
)


@pytest.mark.integration
def test_real_training_freeze_evaluation_and_trusted_reload(tmp_path: Path) -> None:
    data, run, reports = (tmp_path / n for n in ("data", "run", "reports"))
    generate_experiment(data, ExperimentConfig(samples=6000, minimum_positives=10, epochs=3))
    parts = json.loads((data / "partitions.json").read_text())
    assert len(parts["test"]) == 900
    assert "probability" not in (data / "observations.csv").read_text().splitlines()[0]
    train_experiment(data, run)
    frozen = (run / "decision.json").read_bytes()
    report = evaluate_experiment(data, run, reports)
    assert isinstance(report["candidates"], dict)
    assert set(cast(dict[str, object], report["candidates"])) == {
        "logistic",
        "torch",
        "prior",
        "generator",
    }
    support = cast(dict[str, dict[str, int | float]], report["partition_support"])
    assert support["train"]["samples"] == 4200
    assert support["validation"]["samples"] == support["test"]["samples"] == 900
    assert sum(int(v["samples"]) for v in support.values()) == 6000
    assert all(v["positives"] >= 10 for v in support.values())
    assert all(0 < v["prevalence"] < 1 for v in support.values())
    currencies = cast(dict[str, dict[str, int | float]], report["prevalence_by_currency"])
    assert all(v["prevalence"] == v["positives"] / v["samples"] for v in currencies.values())
    assert (run / "decision.json").read_bytes() == frozen
    assert (reports / "pr.png").stat().st_size > 100
    assert (reports / "calibration.png").stat().st_size > 100
    model = load_bundle(run / "bundle")
    rows = [{"amount_minor": 1000, "currency": "EUR"}, {"amount_minor": 15000, "currency": "JPY"}]
    np.testing.assert_allclose(
        model.predict(rows), load_bundle(run / "bundle").predict(rows), atol=1e-6
    )
    assert np.isfinite(model.predict(rows)).all()
    blob = run / "bundle" / "preprocessor.joblib"
    blob.write_bytes(blob.read_bytes() + b"corrupt")
    with pytest.raises(ValueError, match="integrity"):
        load_bundle(run / "bundle")


@pytest.mark.integration
def test_generate_cli_and_no_accidental_overwrite(tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"samples": 6000, "minimum_positives": 10, "epochs": 1}))
    cmd = [
        sys.executable,
        "-m",
        "fraud_ml",
        "generate",
        "--config",
        str(config),
        "--data-dir",
        str(tmp_path / "data"),
    ]
    first = subprocess.run(cmd, text=True, capture_output=True, check=False)
    assert first.returncode == 0, first.stderr
    again = subprocess.run(cmd, text=True, capture_output=True, check=False)
    assert again.returncode != 0


def test_bundle_requires_trusted_well_formed_manifest(tmp_path: Path) -> None:
    (tmp_path / "manifest.json").write_text(json.dumps({"files": {"../escape.joblib": "x"}}))
    with pytest.raises(ValueError):
        load_bundle(tmp_path)


@pytest.mark.integration
def test_export_must_match_in_memory_torch_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import torch

    from fraud_ml.networks import MLP

    def wrong_checkpoint(*args: object, **kwargs: object) -> dict[str, torch.Tensor]:
        return {k: torch.zeros_like(v) for k, v in MLP().state_dict().items()}

    data = tmp_path / "data"
    generate_experiment(data, ExperimentConfig(samples=6000, minimum_positives=10, epochs=2))
    monkeypatch.setattr(torch, "load", wrong_checkpoint)
    with pytest.raises(ValueError, match="parity"):
        train_experiment(data, tmp_path / "run")
