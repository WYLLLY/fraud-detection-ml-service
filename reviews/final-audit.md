# Fraud ML — remediation audit

**Date** 2026-11-14
**Base** `e0c3f660d965b90c72601e79b22aab2d2ba3f2df`
**Verdict** **APPROVE WITH CHANGES** for local synthetic-risk demonstrations

| Severity | Evidence, impact and resolution |
| --- | --- |
| Medium | The README reproduction targeted the committed evaluation directory. It now writes reports under `.local/`, and the regression checks that committed evidence is preserved. |
| Medium | Score inference had a semaphore but request admission and body parsing could consume resources first. The API now admits at most 8 pending scores per worker, limits each body to 1,024 bytes and applies a 2-second read deadline. Tests cover limits, queue pressure and configured route prefixes. |
| Medium | The image policy still expires on 2026-11-28. Base and build tooling now use verified digests, with weekly scans. Review new distribution fixes and rebuild before expiry. The raw report and policy decision stay visible. |
| Medium | The lock now includes OpenTelemetry API 1.45.2 after a newly published advisory. [Upstream release](https://github.com/open-telemetry/opentelemetry-python/releases/tag/v1.45.2) |
| Low | The audited base already contains the corrected Payment demo status. The local operational note now reflects the current image verification. |

| Check | Result | Evidence |
| --- | --- | --- |
| Maintained suite | PASS | 56 unit, 24 API and 67 integration cases. 147 passed, 0 failed, 0 skipped. A restricted-shell attempt failed three socket fixtures with `EPERM`. The localhost-enabled run resolved them. |
| Reproduced experiment | PASS | Generated and trained on the 60,000-row synthetic configuration, then ran evaluation. Logistic selected. Its average precision was 0.09061 and the prior baseline was 0.04389. The generator-only baseline scored 0.09179. |
| Local Payment-to-Fraud CLI | PASS | A real isolated Payment API returned a terminal fictitious payment. The genuine Fraud endpoint scored only amount and currency. The Payment token was confined to Payment and returned balances, payment and ledger page were unchanged. This cross-project run preceded the final telemetry dependency update. |
| Static and dependencies | PASS | Ruff, pyright, Bandit, actionlint and installed Python advisory inventory. |
| Docker and runtime policy | PASS | Exact ARM64 container built, started and scored three records. Predictions matched the bundle. The local guard accepted 44 reviewed findings and independently verified three SQLite fixes. |
| Unfiltered image policy gate for zero High or Critical findings | FAIL | The raw Trivy scan returned 47 High package/advisory pairs. The scoped local decision expires on 2026-11-28. |
| Hosted CI, real-fraud utility and production load | SKIPPED | Local test evidence and synthetic evaluation only. |

Portfolio use supports reproducible evaluation, leakage controls, calibrated reporting and bounded serving. Synthetic labels and the generator-only baseline constrain claims about model signal and live fraud accuracy.
