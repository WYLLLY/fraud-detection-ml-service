---
name: fraud-model-evaluation
description: Evaluate Fraud ML candidates, calibration and generator reference, select validation-only thresholds and package the trusted model bundle; not data generation or API implementation.
---

# Fraud Model Evaluation

Read AGENTS.md and M1 selection/report/bundle rules. Work from candidate predictions plus saved split IDs; distinguish a review from authorization to rerun a full experiment.

- Verify identical held-out rows and provenance for sklearn, torch, constant prior and generator probability. The latter is a reference distribution, not a trained or deployable predictor. A finite test sample need not rank that reference best on every metric.
- Select by validation AP using the exact 0.01 absolute MLP margin; use validation scores for F1 threshold and precision/highest-threshold tie-breaks. Freeze candidate checkpoint, transform and thresholds before final test. No train+validation refit or test-driven reselection.
- Report precision/recall/F1/confusion at 0.5 and selected thresholds; AP and trapezoidal PR-AUC distinctly; Brier/log loss plus ten-quantile reliability diagram with group counts. Handle tied quantiles explicitly and report fewer nonempty groups when necessary; do not fabricate bins or omit sparse regions silently.
- Undefined metrics need an explicit cause and JSON-safe representation; forbid NaN/Infinity output. Show prevalence and sample/positive counts. Low Brier alone is not proof of calibration; no recalibrator is fitted in v1.
- Measure CPU latency with model/preprocessing loaded outside the timed warm path and label cold versus warm measurements honestly. Report hardware and batch size; no production SLO claim.
- The plan's constant-baseline validation gate controls promotion. On failure preserve the evidence and diagnose rather than changing generator/seeds/test or promoting an unqualified bundle.
- Save transform, feature order/domain, model, threshold and manifest with code/config/environment/dataset/split hashes. Derive immutable version from a canonical manifest excluding its own digest field to avoid a recursive hash. Verify referenced file hashes before loading.

Test metric computations against small known cases, threshold ties, undefined cases, provenance mismatch and serialization/API parity. The serving layer consumes the selected trusted bundle; it never receives labels or p(x). Actual Payment records have no known synthetic label and cannot validate prediction correctness.
