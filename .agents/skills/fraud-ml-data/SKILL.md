---
name: fraud-ml-data
description: Build or review the synthetic dataset, leakage-safe splits, preprocessing and scikit-learn baseline for Fraud ML M1; not PyTorch optimization or HTTP serving.
---

# Fraud ML Data

Read root AGENTS.md and M1 in docs/FRAUD_ML_PLAN.md. The plan supplies all experiment constants; do not duplicate or change them here.

1. Inspect the generator configuration and data schema before edits. Pin the 60,000-row experiment and generation/split seeds, declared currency scales and exact Bernoulli formula.
2. Keep row identity and y outside X; keep p(x) in a separate reference file joined only in evaluation. Allowlist predictors instead of dropping a few known forbidden columns.
3. Freeze stratified 70/15/15 row IDs before fitting. Check class support and actual prevalence. Repeated feature pairs are legitimate independent draws; copied row IDs across splits are leakage.
4. Fit log1p/scaler on train only. One-hot order is EUR, USD, JPY, producing four inputs. Persist the fitted transform; share it across sklearn, torch and inference rather than reimplementing three transforms.
5. Build the constant prior and fixed logistic baseline, record convergence. Do not add SMOTE, weighting, ULB PCA, extra features or hyperparameter sweeps.
6. Record data/config/split/environment hashes. A failed class-support check triggers diagnosis, not seed shopping. Do not claim chronological validation for iid synthetic data.

Use behavioral TDD: fail on contamination by y/p(x), overlapping row IDs, held-out-stat fitting, invalid currencies/amounts, wrong feature order and non-reproducible seeded generation. Verify labels overlap stochastically; never require every tiny fixture to contain a rare class by chance.

Hand off fitted candidate pipelines, frozen partition IDs and manifests to fraud-model-evaluation. Run only the authorized milestone; full experiment execution requires implementation/experiment scope, not a read-only review request.
