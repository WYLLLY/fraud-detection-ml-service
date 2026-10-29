# Fraud ML — synthetic-risk experiment

An independent Python portfolio project comparing logistic regression and a CPU PyTorch MLP on explicitly synthetic risk labels. **All three milestones are implemented and locally verified:** M1 data/training/evaluation, M2 local FastAPI inference and M3 read-only scoring of an existing Payment fixture. See [the global independent review](reviews/GLOBAL_REVIEW.md) for final verification and [PR #3](https://github.com/WYLLLY/fraud-detection-ml-service/pull/3) for M3 integration status. No public backend or production fraud validation is claimed.

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

The CI audits an exact inventory of installed versions through `pip-audit --no-deps --disable-pip --strict`. The inventory records exact installed builds; official Linux torch +cpu is looked up against its public upstream version, with no advisory suppression. The local editable `fraud-ml` project is excluded from advisory lookup, not from source review. No automatic upgrade/fix or advisory suppression is used. Small integration fixtures test actual training/export/CLI behavior, not benchmark efficacy.

Only load bundles produced by this project in a trusted local directory. Joblib may execute code. File digests verify a trusted manifest's integrity, not an untrusted publisher's authenticity. Bundles have no upload/download endpoint. Oracle references and raw data are excluded from deployed bundles; no Payment credentials or SQL access exist in M1.

The selected bundle includes immutable feature schema/order, domains, threshold, data/split/config/environment/source identities, validation metrics and model files. Its manifest digest excludes its own version field. Preserve the trusted bundle and locked environment together.

See [M1 test matrix](docs/M1_TEST_MATRIX.md), [verification](docs/M1_VERIFICATION.md) and [actual experiment report](docs/results/M1/REPORT.md) for evidence and limitations. Local inference evidence follows below; real Payment integration belongs to M3.

## M2 local inference

M2 provides `POST /score` and `GET /health`. Use the trusted M1 bundle produced above:

```sh
FRAUD_MODEL_DIR=artifacts/m1/bundle uv run --frozen uvicorn fraud_ml.api:create_app \
  --factory --host 127.0.0.1 --port 8002 --workers 1 --no-access-log --no-proxy-headers
```

```sh
curl --fail http://127.0.0.1:8002/health
curl --fail http://127.0.0.1:8002/score -H 'Content-Type: application/json' \
  --data '{"amount_minor":1000,"currency":"EUR"}'
```

The response contains a finite score, `low_synthetic_risk`/`elevated_synthetic_risk`, immutable model/schema versions and explicit synthetic/experimental markers. Scores at or above the saved threshold receive the elevated indicator. There is no authorization/rejection of payments.

Invalid shape/types/currency/extras return 422. Valid financial amounts outside the synthetic training range return 422 with `outside_training_domain`. Missing/corrupt/incompatible artifacts stop startup. Backend failures return generic 500 `inference_failed`; a concurrent inference receives 503 `inference_busy`. No failure becomes zero risk. Request events log only route/status/duration/version/error code. Access logs are disabled to avoid raw URLs/query strings.

Docker uses a versioned Python 3.12 slim base, current distribution security updates and the frozen Python lockfile. No data/model/secret is copied into the image. Run the trusted bundle read-only:

```sh
docker compose up --build --wait
uv run --frozen python scripts/smoke_api.py --bundle artifacts/m1/bundle
docker compose down
```

For this host's dedicated engine, prefix Compose commands with `DOCKER_CONTEXT=colima-fraud-ml`. The service publishes only loopback port 8002, runs UID 10001 with read-only root and model mount, drops capabilities and limits resources. Authentication is intentionally absent for this local-only MVP; broader network exposure requires a separate decision.

See [M2 verification](docs/M2_VERIFICATION.md) and [independent review](reviews/M2-review.md). No training happens through HTTP or service startup.

The image scan is **not clean**: eight inherited HIGH Debian advisories remain, with no stable fix at review time. The raw Trivy failure is preserved. A separate, tested policy accepts only exact reviewed package/advisory versions under verified local runtime restrictions until **28 November 2026**. Any critical/new/fixable/expired exception, changed serving code or missing mitigation fails CI. See [the dated security decision](docs/M2_IMAGE_SECURITY.md); this is a bounded local portfolio exception, not production approval.

## M3 read-only Payment demo

Requires the real local Payment API, a token for the owner of an existing payment, and the local ML API above. Set `PAYMENT_API_TOKEN` securely in the environment; never put its value in command arguments, a URL, a report or source control. For an interactive Bash/Zsh session, `read -rs PAYMENT_API_TOKEN` followed by `export PAYMENT_API_TOKEN` avoids placing the value in shell history.

```sh
uv run --frozen fraud-ml demo --payment-id YOUR_EXISTING_PAYMENT_UUID \
  --payment-api-url http://127.0.0.1:8000 --fraud-api-url http://127.0.0.1:8002
unset PAYMENT_API_TOKEN
```

The client makes one authenticated Payment GET, validates the existing response and identity, and forwards only `amount_minor`/`currency`. A token-free ML health GET pins the model version before the token-free score POST. Only distinct loopback service ports are permitted; userinfo, paths, queries, fragments and remote origins are rejected. Separate clients disable redirects, retries and environment proxies. Every HTTP call has a 1 s connect timeout and a genuine 5 s total deadline covering headers and body. Response bodies are bounded to 16 KiB.

Success prints JSON containing the payment ID, finite score, advisory indicator, model/schema versions and explicit synthetic markers, plus the required notice: “Score expérimental issu de données synthétiques ; aucune validation de fraude réelle ; aucun effet sur le paiement.” No label or generator probability is attached to that payment. Failure prints only `Score unavailable: <safe_code>` to stderr, exits nonzero and emits no substitute score.

Authentication, missing payments, incompatible data, out-of-domain features, redirects, unavailable services, malformed/version-mismatched responses and total deadlines all cause abstention. The client never creates, retries, cancels or finalizes a payment, logs in automatically, imports Payment internals or accesses SQL. It imports neither the synthetic generator nor training modules. Independent fixture preparation on a dedicated fictional test stack is separate from this command; any required authorization must be resolved before preparation.

**Recorded real local demonstration: PASS (29 October 2026).** A separately prepared fictional 15 EUR payment was already succeeded before scoring. The standard CLI returned 0.011041127797303131; observational verification confirmed the same payment/wallet responses and returned ledger-history page before/after, one Payment GET and token-free ML calls. No real money was spent and no payment label or correctness claim is attached to the score. Independent review approved local M3 acceptance; 134 maintained tests passed again with zero failures/errors/skips.

See [the local demo guide](docs/M3_LOCAL_DEMO.md), [M3 acceptance matrix](docs/M3_TEST_MATRIX.md), [M3 verification](docs/M3_VERIFICATION.md) and [real-service evidence](docs/evidence/M3-real-demo.json). Fixture preparation is separate from the read-only scoring command. The portfolio can show this evidence publicly while the source stays private. A proposed free browser-side scorer would require exporting the selected model and testing Python/JavaScript parity; it is not implemented by this milestone. No new cloud job, push, merge or hosting deployment was performed during local completion.
