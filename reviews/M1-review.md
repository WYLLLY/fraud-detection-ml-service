# M1 independent review

Date: 29 October 2026 (Europe/Paris). Reviewer: separate `m1_review` subagent using fraud-review and adversarial-review. Read-only scope: M1 implementation, tests and TDD evidence. No application edits, Payment calls or full experiment by the reviewer.

## Initial verdict: REQUEST CHANGES

The reviewer identified three confirmed gaps:

1. **Medium — export parity evidence:** two reloads of the same bundle did not prove equivalence to the in-memory candidate evaluated during training.
2. **Medium — reporting support:** explicit train/validation/test positive counts and global/per-currency prevalence were missing from the consolidated report.
3. **Low — single-class AP:** all-positive labels incorrectly produced undefined AP rather than 1.

Initial independent regression: 24 passed, 0 failures, 0 errors, 0 skipped (25.97 seconds).

## Corrections and re-review: APPROVE

The primary agent added behavioral regressions before fixes. `docs/evidence/M1-D-red.txt` shows a deliberately wrong exported torch checkpoint was not rejected; `M1-D-green.txt` records its rejection after parity checks for both candidates and the transform. E Red/Green evidence covers missing report support and all-positive metrics.

The reviewer independently inspected both candidate export comparisons and the selected-bundle comparison, all at `rtol=0, atol=1e-6`. Reporting now includes split/global/currency support. The all-positive known case checks AP and trapezoidal PR-AUC both equal 1.

Independent re-verification:

```text
pytest tests/unit/test_learning.py tests/integration/test_experiment.py -q
10 passed in 25.83s
0 failures, 0 errors, 0 skipped
ruff check .
All checks passed!
ruff format --check .
31 files already formatted
```

Final reviewer verdict: **APPROVE for the corrected implementation scope; all three findings resolved; no remaining significant finding identified.** The reviewer confirmed train-only preprocessing, validation-only selection, copied best checkpoints, closed input schema, trusted artifact validation, inference code without generator imports and no financial execution path. Responsibilities and the Scorer protocol were judged proportionate to this small project.

The approval is scoped to reviewed code and corrections. The full experiment, final strict types/security/regression and durable results are primary-agent evidence documented in `docs/M1_VERIFICATION.md`, not independently executed by the reviewer. No remote CI result is claimed.

## Linux CI advisory inventory correction

Independent follow-up verdict: **APPROVE**. The five-case Red evidence was inspected; the reviewer ran the five new tests (5 passed), targeted Ruff/format, and the inventory script (66 installed package records on macOS, no version mapping needed there). The reviewer verified uv.lock's official Linux CPU source and that only torch's exact +cpu suffix maps to the public advisory version. Strict audit remains active with no ignored advisory, package upgrade or hidden omission. Linux audit completion is established separately by GitHub CI, not this review.
