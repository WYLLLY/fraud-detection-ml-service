"""Persisted experiment phases: generate, fit/freeze, and evaluate without fitting."""

import csv
import importlib.metadata
import platform
import shutil
import warnings
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, cast

import numpy as np
import torch
from sklearn.exceptions import ConvergenceWarning  # pyright: ignore[reportMissingTypeStubs]

from fraud_ml.artifact_io import digest, identity, read_json, verify_files, write_json
from fraud_ml.bundle import load_bundle
from fraud_ml.data import (
    Observation,
    Partitions,
    feature_rows,
    generate,
    labels,
    select_rows,
    split,
)
from fraud_ml.evaluation import choose_candidate, metrics, threshold_for
from fraud_ml.features import DOMAINS, FEATURE_ORDER, Preprocessor
from fraud_ml.library_io import load_local, save_local
from fraud_ml.models import LogisticScorer, Scorer, TorchScorer
from fraud_ml.training import TrainingConfig, train_torch


@dataclass(frozen=True)
class ExperimentConfig:
    samples: int = 60000
    generation_seed: int = 42
    split_seed: int = 43
    training_seed: int = 44
    epochs: int = 50
    patience: int = 5
    batch_size: int = 256
    learning_rate: float = 0.001
    minimum_positives: int = 50

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if name == "learning_rate":
                if type(value) not in (int, float) or not np.isfinite(value) or value <= 0:
                    raise ValueError("Invalid learning rate")
            elif type(value) is not int or value < (
                0 if "seed" in name or name == "minimum_positives" else 1
            ):
                raise ValueError(f"Invalid experiment field {name}")

    def training(self) -> TrainingConfig:
        return TrainingConfig(
            self.epochs, self.patience, self.batch_size, self.learning_rate, self.training_seed
        )


def save_csv(path: Path, header: Sequence[str], rows: Sequence[Sequence[object]]) -> None:
    with path.open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def generate_experiment(directory: Path, config: ExperimentConfig) -> None:
    if directory.exists():
        raise ValueError("Refusing to overwrite existing experiment data")
    generated = generate(config.samples, config.generation_seed)
    partitions = split(generated.observations, config.split_seed, config.minimum_positives)
    directory.mkdir(parents=True)
    save_csv(
        directory / "observations.csv",
        ["row_id", "amount_minor", "currency", "label"],
        [(r.row_id, r.amount_minor, r.currency, r.label) for r in generated.observations],
    )
    save_csv(
        directory / "reference.csv",
        ["row_id", "probability"],
        [
            (r.row_id, p)
            for r, p in zip(generated.observations, generated.probabilities, strict=True)
        ],
    )
    write_json(directory / "config.json", asdict(config))
    write_json(directory / "partitions.json", asdict(partitions))
    files = {
        name: digest(directory / name)
        for name in ("observations.csv", "reference.csv", "config.json", "partitions.json")
    }
    write_json(directory / "manifest.json", {"schema": "synthetic-data-v1", "files": files})


def read_data(
    directory: Path,
) -> tuple[tuple[Observation, ...], Partitions, ExperimentConfig, dict[str, Any]]:
    manifest = read_json(directory / "manifest.json")
    expected = {"observations.csv", "reference.csv", "config.json", "partitions.json"}
    if manifest.get("schema") != "synthetic-data-v1" or set(manifest.get("files", {})) != expected:
        raise ValueError("Invalid data manifest")
    verify_files(directory, manifest["files"])
    config = ExperimentConfig(**read_json(directory / "config.json"))
    with (directory / "observations.csv").open(newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["row_id", "amount_minor", "currency", "label"]:
            raise ValueError("Invalid observation schema")
        observations = tuple(
            Observation(int(r["row_id"]), int(r["amount_minor"]), r["currency"], int(r["label"]))
            for r in reader
        )
    parts = read_json(directory / "partitions.json")
    partitions = Partitions(*(tuple(parts[k]) for k in ("train", "validation", "test")))
    # Validate actual persisted membership, not just an asserted hash.
    if (
        partitions != split(observations, config.split_seed, config.minimum_positives)
        or len(observations) != config.samples
    ):
        raise ValueError("Invalid frozen partitions")
    return observations, partitions, config, manifest


def environment() -> dict[str, object]:
    root = Path(__file__).resolve().parents[2]
    lock = root / "uv.lock"
    source = {str(p.relative_to(root)): digest(p) for p in sorted((root / "src").rglob("*.py"))}
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "packages": {
            n: importlib.metadata.version(n)
            for n in ("numpy", "pandas", "torch", "scikit-learn", "joblib")
        },
        "lock_sha256": digest(lock),
        "source_sha256": identity(source),
        "source_files": source,
        "device": "cpu",
        "torch_threads": torch.get_num_threads(),
        "dtype": "torch.float32 / numpy.float64",
    }


def train_experiment(data_dir: Path, output: Path) -> None:
    if output.exists():
        raise ValueError("Refusing to overwrite existing trained run")
    observations, parts, config, manifest = read_data(data_dir)
    train, val = select_rows(observations, parts.train), select_rows(observations, parts.validation)
    preprocessor = Preprocessor().fit(feature_rows(train))
    x, vx = preprocessor.transform(feature_rows(train)), preprocessor.transform(feature_rows(val))
    y, vy = labels(train), labels(val)
    logistic = LogisticScorer()
    start = perf_counter()
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        logistic.fit(x, y)
    logistic_seconds = perf_counter() - start
    start = perf_counter()
    trained = train_torch(x, y, vx, vy, config.training())
    torch_seconds = perf_counter() - start
    candidates: dict[str, Scorer] = {"logistic": logistic, "torch": TorchScorer(trained.model)}
    thresholds: dict[str, float] = {}
    validation: dict[str, dict[str, object]] = {}
    for name, model in candidates.items():
        p = model.scores(vx)
        thresholds[name] = threshold_for(vy, p)
        validation[name] = metrics(vy, p, thresholds[name])
    lap, tap = validation["logistic"]["ap"], validation["torch"]["ap"]
    if not isinstance(lap, float) or not isinstance(tap, float):
        raise ValueError("Undefined validation ranking")
    selected = choose_candidate(lap, tap)
    prior = float(np.mean(y))
    prior_ap = metrics(vy, np.full(len(vy), prior))["ap"]
    selected_ap = validation[selected]["ap"]
    eligible = (
        isinstance(selected_ap, float) and isinstance(prior_ap, float) and selected_ap > prior_ap
    )
    output.mkdir(parents=True)
    save_local(preprocessor, output / "preprocessor.joblib")
    save_local(logistic, output / "logistic.joblib")
    torch.save(trained.model.state_dict(), output / "torch.pt")
    # Compare each exported candidate against the evaluated in-memory candidate,
    # including the reloaded transform; two reloads of the same bad file are not parity.
    restored_transform = load_local(output / "preprocessor.joblib")
    restored_logistic = load_local(output / "logistic.joblib")
    if not isinstance(restored_transform, Preprocessor) or not isinstance(
        restored_logistic, LogisticScorer
    ):
        raise ValueError("Export parity: unexpected candidate types")
    from fraud_ml.networks import MLP

    restored_network = MLP()
    restored_network.load_state_dict(
        torch.load(output / "torch.pt", weights_only=True, map_location="cpu"), strict=True
    )
    restored: dict[str, Scorer] = {
        "logistic": restored_logistic,
        "torch": TorchScorer(restored_network),
    }
    parity: dict[str, float] = {}
    parity_rows = feature_rows(val[:32])
    for name, scorer in candidates.items():
        expected_scores = scorer.scores(preprocessor.transform(parity_rows))
        actual_scores = restored[name].scores(restored_transform.transform(parity_rows))
        if not np.allclose(expected_scores, actual_scores, rtol=0, atol=1e-6):
            raise ValueError(f"Export parity failed for {name}")
        parity[name] = float(np.max(np.abs(expected_scores - actual_scores)))
    files = {n: digest(output / n) for n in ("preprocessor.joblib", "logistic.joblib", "torch.pt")}
    decision = {
        "selected": selected,
        "eligible": eligible,
        "thresholds": thresholds,
        "validation": validation,
        "prior": prior,
        "export_parity_max_abs_error": parity,
        "data_identity": identity(manifest),
        "data_manifest": manifest,
        "files": files,
        "config": asdict(config),
        "training_seconds": {"logistic": logistic_seconds, "torch": torch_seconds},
        "torch_best_epoch": trained.best_epoch,
        "torch_validation_ap": trained.history,
        "environment": environment(),
        "test_accessed_for_selection": False,
    }
    # Persist decisions before any held-out evaluation; evaluate never fits.
    write_json(output / "decision.json", decision)
    if eligible:
        bundle_dir = output / "bundle"
        bundle_dir.mkdir()
        shutil.copyfile(output / "preprocessor.joblib", bundle_dir / "preprocessor.joblib")
        filename = "model.joblib" if selected == "logistic" else "model.pt"
        shutil.copyfile(
            output / ("logistic.joblib" if selected == "logistic" else "torch.pt"),
            bundle_dir / filename,
        )
        metadata = {
            "schema": "synthetic-risk-v1",
            "kind": selected,
            "threshold": thresholds[selected],
            "feature_order": list(FEATURE_ORDER),
            "domains": DOMAINS,
            "data_identity": identity(manifest),
            "config": asdict(config),
            "validation": validation,
            "environment": decision["environment"],
            "files": {n: digest(bundle_dir / n) for n in ("preprocessor.joblib", filename)},
        }
        write_json(bundle_dir / "manifest.json", {**metadata, "version": identity(metadata)})
        loaded = load_bundle(bundle_dir)
        if not np.allclose(
            loaded.predict(parity_rows),
            candidates[selected].scores(preprocessor.transform(parity_rows)),
            rtol=0,
            atol=1e-6,
        ):
            raise ValueError("Selected bundle parity failed")


def evaluate_experiment(data_dir: Path, output: Path, report_dir: Path) -> dict[str, object]:
    if report_dir.exists():
        raise ValueError("Refusing to overwrite evaluation evidence")
    decision = read_json(output / "decision.json")
    observations, parts, _, manifest = read_data(data_dir)
    if decision["data_identity"] != identity(manifest):
        raise ValueError("Evaluation dataset differs from frozen training lineage")
    verify_files(output, decision["files"])
    preprocessor = load_local(output / "preprocessor.joblib")
    logistic = load_local(output / "logistic.joblib")
    if not isinstance(preprocessor, Preprocessor) or not isinstance(logistic, LogisticScorer):
        raise ValueError("Invalid candidate artifacts")
    from fraud_ml.networks import MLP

    network = MLP()
    network.load_state_dict(
        torch.load(output / "torch.pt", weights_only=True, map_location="cpu"), strict=True
    )
    test = select_rows(observations, parts.test)
    x, y = preprocessor.transform(feature_rows(test)), labels(test)
    with (data_dir / "reference.csv").open(newline="") as stream:
        reference = {int(r["row_id"]): float(r["probability"]) for r in csv.DictReader(stream)}
    scores = {
        "logistic": logistic.scores(x),
        "torch": TorchScorer(network).scores(x),
        "prior": np.full(len(y), float(decision["prior"])),
        "generator": np.asarray([reference[r.row_id] for r in test], dtype=np.float64),
    }
    candidates: dict[str, dict[str, object]] = {}
    for name, p in scores.items():
        threshold = float(decision["thresholds"].get(name, 0.5))
        candidates[name] = {
            "at_0_5": metrics(y, p),
            "at_selected_threshold": metrics(y, p, threshold),
        }
    # Warm, batch-one latency includes preprocessing and model, not disk loading.
    latency: dict[str, object] = {}
    for name, scorer in {"logistic": logistic, "torch": TorchScorer(network)}.items():
        rows = feature_rows(test[:1])
        scorer.scores(preprocessor.transform(rows))
        timings: list[float] = []
        for _ in range(100):
            start = perf_counter()
            scorer.scores(preprocessor.transform(rows))
            timings.append((perf_counter() - start) * 1000)
        latency[name] = {
            "warm_batch_size": 1,
            "iterations": 100,
            "p50_ms": float(np.quantile(timings, 0.5)),
            "p95_ms": float(np.quantile(timings, 0.95)),
        }
    prevalence: dict[str, dict[str, int | float]] = {
        currency: {
            "samples": sum(r.currency == currency for r in observations),
            "positives": sum(r.label for r in observations if r.currency == currency),
        }
        for currency in DOMAINS
    }
    partition_support = {}
    for name, ids in (
        ("train", parts.train),
        ("validation", parts.validation),
        ("test", parts.test),
    ):
        rows = select_rows(observations, ids)
        positive_count = sum(r.label for r in rows)
        partition_support[name] = {
            "samples": len(rows),
            "positives": positive_count,
            "prevalence": positive_count / len(rows),
        }
    for counts in prevalence.values():
        counts["prevalence"] = counts["positives"] / counts["samples"]
    report: dict[str, object] = {
        "selected": decision["selected"],
        "eligible": decision["eligible"],
        "decision_sha256": digest(output / "decision.json"),
        "data_identity": identity(manifest),
        "candidates": candidates,
        "latency": latency,
        "prevalence_by_currency": prevalence,
        "partition_support": partition_support,
        "global_prevalence": sum(r.label for r in observations) / len(observations),
        "environment": decision["environment"],
        "training_seconds": decision["training_seconds"],
        "limitations": (
            "Synthetic iid risk only. No real fraud efficacy; generator reference is never served."
        ),
    }
    report_dir.mkdir(parents=True)
    write_json(report_dir / "metrics.json", report)
    from fraud_ml.plots import plot_evaluation

    plot_evaluation(y, scores, report_dir)
    table = [
        "# Synthetic-risk evaluation",
        "",
        "No real fraud detection claim. Selection was frozen before test.",
        "",
        "| Candidate | AP | Precision | Recall | F1 | Brier |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for name, records in candidates.items():
        m = cast(dict[str, object], records["at_selected_threshold"])
        table.append(
            "| "
            + " | ".join(
                str(v) for v in (name, m["ap"], m["precision"], m["recall"], m["f1"], m["brier"])
            )
            + " |"
        )
    table += [
        "",
        f"Selected: {decision['selected']}; eligible: {decision['eligible']}.",
        "",
        "![PR curve](pr.png)",
        "",
        "![Calibration](calibration.png)",
        "",
        (
            "See metrics.json for threshold-0.5 metrics, trapezoidal PR-AUC, log loss, "
            "calibration counts, sample support, latency and environment."
        ),
    ]
    (report_dir / "REPORT.md").write_text("\n".join(table) + "\n")
    return report
