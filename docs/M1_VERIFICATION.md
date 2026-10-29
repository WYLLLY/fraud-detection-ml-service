# M1 verification — data and learning

Date: 29 October 2026 (Europe/Paris). Scope: M1 only. Status: **local implementation/verification PASS; remote CI pending publication**. M2/M3 were not implemented during this verification.

## Implemented behavior and design

Python 3.12.15 and the frozen uv environment run a 60,000-row synthetic experiment. Data/reference files and disjoint stratified row IDs are persisted before fitting. Predictors are closed to amount/currency; shared train-only preprocessing produces four columns. Logistic regression and CPU 4-16-8-1 PyTorch MLP are actually trained. Validation chooses checkpoint, candidate and threshold before final test. Both exported candidates and the selected bundle are compared to their original in-memory predictors at absolute tolerance 1e-6.

SOLID is applied through focused modules and a small Scorer protocol, not an orchestration framework. Generation, preprocessing, optimization, metrics, persistence, plotting and CLI have separate responsibilities. Pure prediction imports neither generation nor training.

## TDD evidence

Contract-only stubs established importable interfaces before implementation; setup/import failures were not counted as Red. Evidence files were captured before the corresponding behavior was implemented.

| Cycle | Behavioral Red | Green / outcome |
| --- | --- | --- |
| A: generator, schema, partitions, train-only preprocessing | M1-A-red.txt: 16 failed | M1-A-green.txt: 16 passed |
| B: optimization, copied best checkpoint, metrics/selection | M1-B-red.txt: 5 failed | M1-B-green.txt: 5 passed |
| C: persisted phases, actual models, bundle/CLI round trip | M1-C-red.txt: 3 failed | M1-C-green.txt: 24 passed across the combined suite |
| D: wrong exported checkpoint must fail in-memory parity | M1-D-red.txt: 1 failed, expected exception not raised | M1-D-green.txt: 1 passed |
| E: all-positive AP and explicit split/currency support | M1-E-red.txt: 2 failed | M1-E-green.txt: 26 passed across the combined suite |

Refactor extracted the shared domain, inference-safe network/predictor adapters and narrow third-party serialization boundary. Tests were preserved. See [test matrix](M1_TEST_MATRIX.md) and [independent review](../reviews/M1-review.md). Review initially requested changes; all three findings were corrected and the independent re-review verdict is **APPROVE**.

## Final checks

All commands ran from Projet 3. Logs and JUnit results are in docs/evidence.

| Check | Status | Result |
| --- | --- | --- |
| uv sync --frozen --offline | PASS | 67 packages checked; environment not re-resolved |
| .venv/bin/ruff check . | PASS | All checks passed |
| .venv/bin/ruff format --check . | PASS | No formatting changes required |
| .venv/bin/pyright | PASS | Strict src/tests: 0 errors, 0 warnings |
| MPLCONFIGDIR=.local/matplotlib .venv/bin/python -m pytest -q --junitxml=docs/evidence/M1-tests.xml | PASS | **26 passed, 0 failed, 0 errors, 0 skipped**, 8.17 s |
| .venv/bin/bandit -r src -f json -o docs/evidence/M1-bandit.json | PASS | 0 findings, no nosec suppressions |
| Exact installed-environment dependency audit | PASS | No known vulnerabilities; no ignored advisories |
| Full generate/train/evaluate CLI | PASS | 60,000 rows; held-out test evaluated after decision freeze |
| Repeat full training, validation comparison only | PASS | Identical selected candidate, thresholds, torch validation history and predictions (max absolute difference 0) |
| CI workflow structure | PASS | YAML parsed; quality/security/full tiny-fixture regression configured |
| GitHub Actions | SKIPPED at this snapshot | No remote yet; publication/CI is being handled separately under the user's newer instruction |
| API/Docker/Payment execution | SKIPPED — outside M1 | Reserved for M2/M3; no Payment writes |

pip-audit's initial strict editable-environment invocation rejected the local editable package. The successful audit instead used importlib.metadata to inventory every installed distribution except the local unpublished fraud-ml package, then:

```sh
.venv/bin/pip-audit --disable-pip --no-deps --strict \
  -r docs/evidence/M1-audited-environment.txt --progress-spinner off \
  --cache-dir .local/audit-cache -f json -o docs/evidence/M1-dependency-audit.json
```

This queried advisory services without resolution/upgrades. Source security remains covered by Bandit and independent review; the local project is not claimed audited against public package advisories. Initial dependency downloads and Node availability issues were setup failures, not TDD Red. Pyright's Node runtime is now locked through pyright[nodejs].

## Actual experiment

- Train: 42,000 rows / 1,845 positives.
- Validation: 9,000 / 396.
- Final test: 9,000 / 395.
- Overall prevalence: 4.3933%.
- Validation AP: logistic **0.10402746**, MLP **0.11167001**. Difference is below 0.01, so **logistic regression** was selected and eligible before final test.
- Test AP: logistic **0.09061000**, MLP **0.09366839**, constant prior **0.04388889**, generator reference **0.09178707**.
- Selected logistic threshold: **0.09541724789447012**; synthetic precision **0.13059034**, recall **0.18481013**, F1 **0.15303983**; Brier **0.04112307**.
- Export parity: maximum absolute error 0 for both formats.

No numeric quality target or MLP victory was invented. The generator reference is not a learned candidate and is never served. Constant-score trapezoidal PR-AUC is inflated by endpoint interpolation; AP, not that area, determines selection. Calibration plots/quantile counts, all metrics, source/environment/lock hashes and split IDs are preserved in [the experiment report](results/M1/REPORT.md) and its JSON/manifests. Raw data and loadable model artifacts remain excluded from Git under data/ and artifacts/.

The second complete training run checked reproducibility on validation only and did not reselect a model on final test. Current source/lock identities match the original trained-run provenance. Joblib is limited to trusted local release artifacts; file hashes are not publisher authentication. No real-fraud efficacy, production readiness, cross-platform bitwise reproducibility or remote CI success is claimed by local results.

Projet 1's status remains unchanged, including its pre-existing untracked review document. No M2/M3 feature, payment call, migration or financial write was performed in M1.

## Publication and Linux CI follow-up

Private repository: https://github.com/WYLLLY/fraud-detection-ml-service ; PR #1. The first Linux push/PR checks passed quality/regression/Bandit but failed advisory lookup for official torch 2.15.0+cpu, which is absent from PyPI's release metadata. This was an audit lookup error, not a product failure or ignored vulnerability.

`scripts/audit_environment.py` now records both the exact installed version and advisory version, mapping only torch's official +cpu build suffix to the upstream public release. All distributions remain in the audit inventory (except the local editable application); no advisory is suppressed. Custom suffixes and other package versions remain unchanged and therefore fail strict audit if unavailable.

Cycle F: five pre-fix behavioral failures in M1-F-red.txt; full regression after correction: **31 passed, 0 failures/errors/skips** (M1-F-green.txt). Strict Pyright includes scripts, and workflow Bandit also scans scripts. Remote rerun is pending at this evidence snapshot; merge requires green checks and independent review.
