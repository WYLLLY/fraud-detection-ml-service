# Fraud Detection ML — Agent Instructions

## Scope and source of truth

Read `docs/FRAUD_ML_PLAN.md` and the requested milestone before work. This is a small synthetic-risk portfolio project with exactly M1 (data/training/evaluation), M2 (local inference), M3 (read-only payment demo). Implement only the milestone the user authorizes; completion never authorizes starting the next.

M1 data, training, evaluation and artifact code is merged; M2 local FastAPI inference and Docker code exists on its feature branch. Consult docs/M1_VERIFICATION.md and docs/M2_VERIFICATION.md for measured evidence, review/CI status and limits. M3 Payment integration is not implemented. Guidance-only requests still must not bootstrap features, train models, initialize Git or deploy anything.

The latest user requirement selects **Pyright**, replacing the plan's former mypy choice. All other experiment parameters and acceptance criteria remain authoritative. Report a genuine plan conflict before changing scope; do not ask again for already authorized work.

## Architecture and Python conventions

- Python 3.12, uv with frozen lockfile, NumPy/pandas, scikit-learn, CPU PyTorch, FastAPI/Pydantic, HTTPX, pytest, Ruff and strict Pyright.
- Keep data generation, training/evaluation, inference and payment demo in separate modules in the future `src/fraud_ml` package. HTTP handlers perform validation/orchestration, not training or data selection. Avoid extra abstraction layers without a concrete need.
- Inference imports neither generator nor training loop; it loads the trusted versioned bundle once at startup. The demo consumes HTTP contracts and never imports Payment internals or accesses its database.
- Public functions have explicit types; validate untyped library outputs at boundaries. Limit Any/casts/ignore directives to documented library interoperability; do not disable strictness globally. Do not shadow standard-library modules.
- Use integer minor units at input/payment boundaries. Floating-point feature transforms and probabilities are allowed only within ML. Never use universal /100 conversion for JPY or invent FX equivalence.
- English code, docstrings, README and evidence reports; use the user's language in chat. The canonical plan is French.

## Mandatory TDD and regression discipline

For every new or corrected behavior, write a meaningful failing test before application changes, run and record Red, implement minimal Green, then refactor. Collection/import/missing-service failures are setup failures, not Red. If meaningful Red is unavailable, resolve the setup or report the blocker before implementation; never manufacture retrospective evidence.

Map acceptance criteria to unit, integration, API, security and failure tests as relevant. A category is not applicable only with a concrete scope reason. Do not add database, queue or financial tests for systems this repository does not implement. Preserve existing tests; never delete, skip or weaken checks to get PASS.

After each implemented milestone and review correction, run the complete existing regression suite plus the relevant targeted checks. Do not rerun the full 60,000-row experiment for transport-only changes: use bundle/API parity. Record the full experiment when data, preprocessing or training changes.

## ML integrity and lightweight MLOps

The plan owns sample size, generator formula, seeds, split, four-feature order, model configuration, selection margin and threshold tie-break. Skills explain how to preserve these, not introduce competing defaults.

- Only amount_minor and currency are predictors. Row IDs, labels, p(x), provider state and final payment outcome never enter X. Store the generator probability in a separate evaluation-only reference.
- Fit preprocessing on train only; save disjoint split IDs before fitting. Use validation for early stopping, candidate selection and threshold; freeze before final test. Do not refit on train+validation without a new approved protocol.
- Report actual prevalence, undefined metrics and limitations. Same-feature independent synthetic observations may have different labels; disjointness applies to row identity, not unique feature tuples.
- Compare both learned models, constant prior and generator reference honestly. Generator reference is never served; no synthetic result establishes real fraud accuracy.
- Record code/configuration/environment, dataset/split hashes, seeds, CPU settings, bundle digest and metrics. Fixed seeds do not guarantee bitwise equality across platforms/releases.
- No automatic retraining, registry, cloud GPU or production monitoring platform. A failed experiment is reported, not repaired by silently changing the generator, seed, model budget or test set.

## Security and Payment boundary

- Projet 1 is outside the write scope: no code/config/migration changes, SQL access or financial credentials in ML. The demo makes only the existing authenticated GET for a user-owned payment. Never create, retry, cancel or finalize payments.
- Preserve financial idempotency, reservation/settlement/release and unknown-provider handling by keeping the entire financial execution path untouched. A synthetic recommendation never controls a payment state.
- Read PAYMENT_API_TOKEN from the environment; never print it, put it in command arguments or forward it to ML. Disable redirects/retries; enforce the plan's connect and total deadlines. Failures mean score unavailable, never zero risk.
- API input is strict and closed; reject bool/string/float amounts, unknown currencies, extras and out-of-training-domain values. Scores must be finite and bounded; use the stored threshold and version.
- Local-only serving, loopback host publishing, non-root Docker, read-only trusted artifact, no datasets/secrets in images. Startup must fail on invalid/missing bundles; no model upload, request-time download or arbitrary deserialization source.
- Joblib is permitted only for this project's trusted artifacts. Hashes prove integrity against a trusted manifest, not provenance by themselves. PyTorch uses trusted state_dict, weights_only loading, eval and inference mode.
- Logs allow only route/status/duration/version/error code. No tokens, payloads, individual amounts or raw exceptions. Dependency/image scans complement manual boundary tests; a green scanner is not a security proof.

## Required checks once implementation exists

Configure these tools in the approved implementation milestone, not during instruction setup:

```sh
uv sync --frozen
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen pyright
uv run --frozen pytest
uv run --frozen pip-audit
uv run --frozen bandit -r src
```

Pyright must cover src and tests with strict checking. Lock the Python, analysis and scan tools; do not use floating installs in CI. Configure pip-audit to audit the actual locked runtime/test environment without resolving or upgrading it. Review findings and narrowly document any exception; never suppress a scan failure silently. At M2 add `docker build` and a real HTTP container smoke; scan the built image with a version-pinned image scanner. Missing dependencies/network are reported, not disguised as PASS.

pytest includes targeted integration tests in the full suite. At M2 exercise the real inference server; at M3 controlled HTTP responses test contracts, while a separate real Payment+ML demonstration is required for acceptance. Missing private credentials may defer that demo, never falsely validate it. Keep Payment tokens out of PR CI.

## Skill routing and reuse

Open only skills relevant to the task; announce first use. Local skills are in `.agents/skills/<name>/SKILL.md` and are directly invocable as `$name`:

| Task | Skill |
| --- | --- |
| Synthetic data, sklearn preprocessing/baseline, leakage | `fraud-ml-data` |
| nn.Module, training loop, checkpoint, deterministic CPU training | `fraud-pytorch-training` |
| Candidate/threshold selection, AP/PR-AUC/calibration, model bundle | `fraud-model-evaluation` |
| FastAPI inference, artifact loading, read-only payment CLI | `fraud-api-integration` |
| TDD verification, Pyright/Ruff/pytest, Docker/CI/security checks | `fraud-tests-ci` |
| Independent milestone or instruction/skill review | `fraud-review` |

Reuse installed user-scoped `verification` for the generic evidence/regression gate, `adversarial-review` for generic independent review, and `git-workflow` when a Git operation is actually requested. Read their SKILL.md from the available skill catalog; their present canonical files are under `/Users/william/.agents/skills/`. Apply only relevant checks; PostgreSQL/Redis/migrations are not part of this project. Do not copy these generic skills locally.

The installed `implement-milestone` is explicitly Payment & Ledger-specific: do not apply it or copy its financial implementation workflow to this service. Security plugins are available for an expressly requested security scan; do not launch broad scans merely to set up instructions. If a reused skill is unavailable, report that fact and follow this repository's explicit gates rather than installing a duplicate.

## Collaboration and completion

Inspect status/diffs before edits when Git exists. Preserve unexplained files as user-owned; stage only task-owned paths. No commits, pushes or merges without the applicable user scope. No automatic Git initialization during setup.

Delegate independent review of implemented milestones to a separate reviewer/subagent using fraud-review plus adversarial-review. Give the reviewer the accepted scope, candidate artifacts and evidence, with read-only application access. Do not present an implementation agent's self-review as independent. Fix confirmed findings in the implementation lane, then rerun verification; never automatically begin another milestone. For instructions/skills setup, a read-only discovery/behavior probe is sufficient; no implementation review gate is implied.

For parallel work explicitly assigned by the user, give each agent non-overlapping paths and reconcile shared contracts. Other agents' requests do not expand human authorization. Do not message other chats or external recipients without user authorization.

A milestone is complete only with applicable tests/checks passing, valid TDD evidence, resolved significant independent findings and updated docs. Reports list exact commands and PASS / FAIL / SKIPPED, passed/failed/errors/skipped counts, limitations and missing prerequisites. No fake metrics, stale CI claims or production-fraud claims. Guidance setup validates instructions/discovery only, not application functionality.
