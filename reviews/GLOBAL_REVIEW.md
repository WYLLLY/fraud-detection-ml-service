# Global independent review — M1–M3

Date: 29 October 2026 (Europe/Paris). Reviewed implementation: `9850408107367dbd7d8e6ec40ea07069dafa52be`, on `feature/m3-payment-demo`, based on merged M2 `2cfcbdf8a24209ea9848a6abf02fedd8f31b27bb`. Subsequent changes in this delivery are review evidence and documentation only.

**Verdict: APPROVE for the approved local synthetic-risk portfolio scope.** No confirmed Critical, High, Medium or Low implementation defect remains from this review. All three planned milestones are implemented and locally accepted. This verdict does not certify production fraud accuracy, public hosting, an exhaustive Payment ledger audit or a clean container vulnerability scan.

The user explicitly requested M3's merge after requesting this global review. Final push/PR CI and merge are separate delivery steps; [PR #3](https://github.com/WYLLLY/fraud-detection-ml-service/pull/3) is authoritative for their eventual state. M1 and M2 were already merged when this review started. No application changes, Payment mutations, full retraining or public deployment were performed in this review.

## Independent scope and findings

Separate read-only reviewer agents `global_ml_review` and `global_api_review` applied `fraud-review` and the installed `adversarial-review`, using relevant project skills and the approved plan. Neither authored the reviewed implementation or edited application files. The coordinating agent ran the complete regression and quality/security checks and inspected the actual-demo evidence, TDD logs, CI and delivery state.

### M1: data, training and evaluation — APPROVE

Inspected generator/configuration, persisted partitions and reference isolation, train-only preprocessing, both learned candidates, CPU PyTorch optimization/checkpoint restoration, validation-only selection, threshold ties, metric/calibration definitions, serialization parity and experiment provenance.

The independent reviewer loaded the actual persisted 60,000-row experiment and trusted bundle. It verified 42,000/9,000/9,000 partition sizes and data lineage, and independently confirmed the saved train log-amount mean/standard deviation to `1e-12`. It recomputed AP, trapezoidal PR-AUC, Brier and log loss for both learned candidates, the constant prior and generator reference: every value matched the published report to `1e-12`. Selected logistic precision/recall/F1 also matched:

| Quantity | Independently reproduced value |
| --- | ---: |
| Test AP | 0.09061000120467542 |
| Precision | 0.13059033989266547 |
| Recall | 0.1848101265822785 |
| F1 | 0.1530398322851153 |
| Stored threshold | 0.09541724789447012 |

Model version: `f7adeda45315d194650515fcea43bf8e71732a5a582d0cb2e8778db2746a17f2`. Threshold selection also matched an independent brute-force implementation on 2,000 randomized cases, including tied scores and class-degenerate labels.

Concrete safeguards include train-only fitting in `experiment.py`, copied/restored best checkpoints in `training.py`, the strict validation AP margin and deterministic threshold ordering in `evaluation.py`, frozen decisions before final test, and comparison of original and serialized predictors. The generator probability and row IDs never enter model inputs. Low measured precision/recall is disclosed experimental performance, not evidence of a hidden implementation failure or useful real-fraud detection.

### M2/M3: inference and Payment boundary — APPROVE

Inspected trusted bundle validation before deserialization, runtime compatibility, strict closed schemas and synthetic domains, finite scores, inclusive stored threshold, bounded concurrent inference, safe errors and allowlisted logs. Reviewed the actual Projet 1 response schema and owner-filtered GET against the client without changing Projet 1.

The client uses separate Payment and ML connections, sends the bearer only to Payment, forwards only amount/currency, disables retries/redirects/environment proxies, restricts origins to distinct local ports, enforces a five-second deadline through streamed body consumption and caps successful response bodies at 16 KiB. It validates explicit experimental metadata and model-version agreement. Failures abstain rather than emit a substitute score. It does not import Payment internals, query SQL or change payment state.

Independent focused command:

```sh
.venv/bin/python -m pytest -q tests/integration/test_payment_demo.py tests/unit/test_image_policy.py
```

**PASS: 79 passed, 0 failed, 0 errors, 0 skipped; 5.18 s.** No live Payment call was made by either global reviewer.

### Actual-service acceptance evidence

Inspected `M3-real-cli.json`, `M3-real-demo.json`, the retained forwarding probe, fixture preparation/cleanup evidence and the previous independent M3 acceptance review. The ordinary CLI and observed real-transport run agree on model version, fixture identity and score `0.011041127797303131`. The recorded journal contains Payment GET, ML health GET and ML score POST, with token isolation. The terminal Payment and wallet responses were unchanged. The ledger comparison covers only the returned history page: limit 50, offset 0, four entries observed.

The fictional fixture was prepared separately under prior explicit user authorization; zero real money was spent. This review did not recreate it, retrieve a token or rerun the services. The payment has no known synthetic label: the score's correctness cannot be asserted. Evidence establishes the recorded local integration, not a global financial invariant test or current service availability.

## Fresh coordinating verification

Commands ran from the project root against the frozen environment. `UV_CACHE_DIR=.local/uv-cache` was set for uv; pytest also used `MPLCONFIGDIR=.local/matplotlib`. The socket-based suite ran with the required local network permission. No test was removed, weakened or skipped.

| Exact command | Result |
| --- | --- |
| `.local/tools/bin/uv lock --check --offline` | PASS; lock consistent |
| `.local/tools/bin/uv sync --frozen --offline` | PASS; 82 installed packages checked |
| `.local/tools/bin/uv run --frozen ruff check .` | PASS |
| `.local/tools/bin/uv run --frozen ruff format --check .` | PASS; 55 files formatted |
| `.local/tools/bin/uv run --frozen pyright` | PASS; 0 errors, 0 warnings |
| `.local/tools/bin/uv run --frozen pytest -q --junitxml=.local/global-review/tests.xml` | **PASS; 134 passed, 0 failed/errors/skipped; 16.92 s** |
| `.local/tools/bin/uv run --frozen bandit -r src scripts -f json -o .local/global-review/bandit.json` | PASS; 0 findings |
| `/opt/homebrew/bin/actionlint .github/workflows/ci.yml` | PASS |
| `.venv/bin/python scripts/audit_environment.py --output .local/global-review/installed.txt` | PASS; exact installed inventory exported |
| `.venv/bin/pip-audit --disable-pip --no-deps --strict -r .local/global-review/installed.txt --progress-spinner off --cache-dir .local/audit-cache -f json -o .local/global-review/dependency-audit.json` | PASS; no known vulnerabilities, no upgrades/advisory suppression |

Fresh test/JUnit, Bandit, dependency inventory/audit and policy replay results are retained as `docs/evidence/GLOBAL-*`. Audit scope excludes only the local unpublished application from public advisory lookup; source review and Bandit cover application code. The documented official torch CPU build/version normalization remains explicit.

TDD matrices and recorded behavioral Red/Green cycles for M1, M2 and M3 were inspected. They include behavior failures and follow-up regressions for checkpoint parity, class-degenerate metrics, strict experimental metadata, URL port zero and image-policy validation. Setup/import/socket errors are explicitly separated from Red. Historical Red was inspected, not replayed or reconstructed; final Green alone was not treated as proof of test-first chronology.

## Container security and remaining limits

**Raw retained Trivy scan: FAIL, exit 1 — 44 HIGH package occurrences across eight CVEs, zero CRITICAL.** The matching immutable M3 image is `sha256:b181fbdd368dce2f0f0c0f1fc2d5488e0ce4d16d82f7dbd9a0962bfef9dd9df0`. This review did not run a new vulnerability-database scan or Docker build locally.

The policy CLI was freshly replayed against the retained raw scan, local Docker inspection and published in-container proof:

```sh
.venv/bin/python scripts/image_policy.py \
  --scan docs/evidence/M3-image-scan.json \
  --runtime .local/M3-final-local-inspect.json \
  --proof docs/evidence/M3-final-local-runtime.json \
  --policy configs/image-security-policy.json --scanner-exit-code 1 \
  --output .local/global-review/image-policy.json
```

Result: **ACCEPTED_REVIEWED_EXCEPTIONS**, `scanner_clean=false`, unchanged expiry **28 November 2026** and exact reviewed source digest `3412f3d4f27c59cd597248db3e880c9b497a1442d2ed2941516f077c44af0a8c`. An initial replay attempt supplied the runtime-proof JSON in place of Docker inspection and was rejected; correcting that input succeeded. This setup error is neither a product failure nor a clean scan.

Reviewed mitigations include loopback publication, UID10001, read-only root/model, dropped capabilities, no-new-privileges, removed privileged helpers/SUID bits and absent vulnerable optional components. New/fixable/critical/expired findings or changed reviewed source fail the separate policy. CI performs a fresh image build, HTTP smoke and scan on push/PR; its latest successful source checks at review start were the d71deb1 push and PR runs. Final delivery must wait for checks on its new head. No public-exposure approval follows from this exception.

Optional future build reproducibility hardening: the Hatchling build-backend range in `pyproject.toml`, Docker tags and CI Python minor selection permit build-environment drift outside application dependency resolution. Pinning those identities would strengthen provenance; this is not an acceptance blocker and no bitwise cross-platform claim is made.

Full retraining is **SKIPPED / not applicable**: no generator, preprocessing, architecture or training change. Fresh local Docker/Payment execution is **NOT RERUN**: matching retained build/demo evidence is identified above; final push CI supplies fresh container verification. Public API/browser scoring, authentication for public exposure, production monitoring and genuine fraud labels remain outside M1–M3. No additional milestone or paid service is required to call the approved local project complete.
