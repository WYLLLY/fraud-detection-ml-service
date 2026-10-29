# Fraud ML — synthetic-risk experiment

An independent Python portfolio project comparing logistic regression and a CPU PyTorch MLP on explicitly synthetic risk labels. **M1 implements data, training, evaluation and artifact round trips.** FastAPI (M2) and the read-only Payment demo (M3) are not implemented.

No result here demonstrates real fraud detection. The generator's probability is an evaluation-only reference; it is never a model input or a served predictor. Existing Payment records have no known synthetic label.

## Reproduce M1

Requires Python 3.12 and uv 0.12.23. The lockfile pins dependencies, including CPU-only PyTorch wheels on Linux; macOS uses its compatible wheel. Training explicitly runs on CPU. Use a new output directory per experiment; existing outputs are never overwritten.

```sh
uv sync --frozen
export MPLCONFIGDIR="$PWD/.local/matplotlib"
uv run --frozen fraud-ml generate --config configs/experiment.json --data-dir data/m1
uv run --frozen fraud-ml train --data-dir data/m1 --output artifacts/m1
uv run --frozen fraud-ml evaluate --data-dir data/m1 --output artifacts/m1 --report-dir docs/results/M1
```

`generate` freezes data, the separate reference and stratified row-ID partitions. `train` fits only training features, uses validation for checkpoints/model/threshold choices and persists decisions before test evaluation. `evaluate` never trains or reselects a model. It writes JSON metrics and standalone PR/calibration figures. The full 60,000-row experiment is explicit, not a PR CI task.

The canonical experiment is in [the plan](docs/FRAUD_ML_PLAN.md). It fixes seeds 42/43/44, a 70/15/15 split, two predictors, four transformed columns, a 4→16→8→1 MLP and the selection margin. Neither MLP superiority nor a target accuracy is guaranteed.

## Responsibilities and SOLID

- `domain` defines the closed feature/domain contract. `data` handles synthetic generation and row identity.
- `features` fits a serializable train-only transform shared by both candidates. No training/generator import is needed to predict.
- `networks` defines the inference-safe MLP; `training` alone owns optimization and checkpoint selection.
- `models.Scorer` is the small prediction protocol implemented by sklearn and torch adapters. Evaluation/orchestration consumes this contract, rather than framework-specific branching throughout the pipeline.
- `evaluation` computes pure metrics and validation decisions. `experiment` coordinates persisted phases; `cli` only parses commands and reports failures.
- `artifact_io`, `library_io` and `bundle` isolate canonical metadata, trusted serialization and validated loading. `plots` is report-only.

This uses small modules and explicit inputs rather than a service container or a generic MLOps framework. Narrow casts/diagnostic annotations are restricted to incomplete third-party library signatures; strict Pyright remains enabled for application and tests.

## Quality and security

```sh
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen pyright
uv run --frozen pytest
uv run --frozen bandit -r src
```

The CI audits an exact inventory of installed versions through `pip-audit --no-deps --disable-pip --strict`. The local editable `fraud-ml` project is excluded from advisory lookup, not from source review. No automatic upgrade/fix or advisory suppression is used. Small integration fixtures test actual training/export/CLI behavior, not benchmark efficacy.

Only load bundles produced by this project in a trusted local directory. Joblib may execute code. File digests verify a trusted manifest's integrity, not an untrusted publisher's authenticity. Bundles have no upload/download endpoint. Oracle references and raw data are excluded from deployed bundles; no Payment credentials or SQL access exist in M1.

The selected bundle includes immutable feature schema/order, domains, threshold, data/split/config/environment/source identities, validation metrics and model files. Its manifest digest excludes its own version field. Preserve the trusted bundle and locked environment together.

See [M1 test matrix](docs/M1_TEST_MATRIX.md), [verification](docs/M1_VERIFICATION.md) and [actual experiment report](docs/results/M1/REPORT.md) for evidence and limitations. API, Docker runtime and real Payment integration belong to later milestones.
