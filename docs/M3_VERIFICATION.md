# M3 verification — read-only Payment scoring

Verified locally on **29 October 2026 (Europe/Paris)**. **M3 local acceptance: PASS.** The real Payment+ML demonstration, full regression and independent review are complete. Application source remains the reviewed `d71deb1f79013a822e33a3ddcc6399ab1ffc84bf` revision (M2 base `2cfcbdf`). No application, model, preprocessing or training code changed during this completion. M3 has not been merged or publicly deployed by this work.

| Gate | Result |
| --- | --- |
| Behavioral TDD A–D and independent source review | PASS, evidence retained |
| Complete local pytest regression | **134 passed, 0 failed, 0 errors, 0 skipped; 16.91 s** |
| Ruff, formatting, strict Pyright, Bandit | PASS; no type diagnostics or source-scan findings |
| Locked Python dependency audit | PASS at the unchanged reviewed environment; no dependency changes |
| Real standard CLI with actual Payment and ML APIs | **PASS**, experimental score 0.011041127797303131 |
| Read-only request observation and before/after snapshots | **PASS**, as scoped below |
| Independent local-acceptance review | **APPROVE**, no unresolved source finding |
| Image raw scan | **FAIL**, 44 HIGH occurrences/eight CVEs, zero CRITICAL |
| Separate bounded image policy | **ACCEPTED_REVIEWED_EXCEPTIONS**, never a clean scan |
| Public backend or browser scorer | NOT IMPLEMENTED / outside the approved local M3 scope |

## Implementation and TDD

`payment_demo.py` owns validated local HTTP orchestration, bounded responses/deadlines and safe abstention. `cli.py` parses arguments, reads the environment token and renders results; offline experiment imports are lazy. Only amount_minor/currency go to ML. Separate clients disable redirects, retries and environment proxies. A token-free health GET pins model identity before scoring. Every HTTP call has a 1 s connection timeout and a 5 s total deadline enclosing headers and streamed body; successful JSON bodies are limited to 16 KiB. Peer metadata must explicitly identify synthetic experimental scoring. No failure becomes zero risk.

The actual PaymentResponse contract was re-read from Projet 1. The client validates identity, strict financial values, currency, state and dates without importing Payment internals, running SQL, logging in or creating/retrying/cancelling/finalizing a payment. No currency conversion or ground-truth label is invented. Inference and the demonstration import neither generator nor training loop. HTTPX2 was moved from dev to runtime without changing locked versions.

| Cycle | Recorded behavioral Red | Green |
| --- | --- | --- |
| A | 56 failures against a contract-only scaffold, no import/setup failure | 56 passed |
| B | Numeric 1 accepted as the experimental boolean: 1 failed/56 passed | Subsequent 61-case combined run passed |
| C | Missing CLI command and training-import coupling: four behavioral failures | 61 combined client/CLI cases passed |
| D | Review found port 0 reached transport: 1 failed/9 passed | 10 URL cases passed, with no request on invalid URLs |

All earlier M1/M2 regressions were retained. No full 60,000-row retraining was needed or performed. The fresh local 134-case run, JUnit, lint, format, type and Bandit reports are `docs/evidence/M3-final-local-*`. The image/model and installed dependency set are unchanged from the reviewed build. The evidence probe is an opt-in observation artifact, not new product behavior or a CI replacement. Its first setup attempt followed the Python symlink outside the virtual environment; correcting the executable path resolved that import failure. It is not counted as TDD Red.

## Actual local demonstration

The user explicitly authorized one fictional payment of **1,500 EUR minor units (15 simulated EUR), with zero real expenditure**. This superseded the earlier authorization hold. Preparation was separate from M3: Projet 1's existing opt-in seed tool funded dedicated fictional fixtures, and an external setup helper created exactly one payment in the isolated `fraud-m3-payment` Compose project. That operation was not performed by the scoring client. The provider was Projet 1's local HTTP simulator. No source/configuration/migration file in Projet 1 was modified.

The ordinary installed `fraud-ml demo` CLI first succeeded without instrumentation. A second read-only run used the retained observation probe, which calls the original HTTP transport and substitutes no response. Both outputs match exactly. The fixture was already terminal before each scoring run.

| Observed CLI service | Method | Route | Result |
| --- | --- | --- | --- |
| Actual Payment API | GET | /payments/{payment_id} | 200 |
| Actual ML API | GET | /health | 200 |
| Actual ML API | POST | /score | 200 |

Payment token headers appear only on the Payment GET. Only the two expected features reach ML. The inference container has no PAYMENT_API_TOKEN. The probe records no bearer value or payment body. No generator, training or torch module is imported by the CLI process.

- Fixture ID: `6710471a-c545-4390-a346-200827d86d0c`; state **succeeded → succeeded**.
- Full returned payment and wallet responses are byte-identical before/after scoring.
- The **returned ledger-history page** is also byte-identical: default limit 50, offset 0, four entries observed. This is not a global or exhaustive ledger audit.
- Score: **0.011041127797303131**; indicator: **low_synthetic_risk**; CLI exit code 0.
- Selected full M1 model: `f7adeda45315d194650515fcea43bf8e71732a5a582d0cb2e8778db2746a17f2`.
- The required French experimental notice is present. No claim that the prediction is correct is made: this payment has no known synthetic label or real-fraud ground truth.

Retained proof: [fixture preparation](evidence/M3-fixture-preparation.json), [ordinary CLI output](evidence/M3-real-cli.json), [real-service observation](evidence/M3-real-demo.json), [probe source](evidence/M3-real-demo-probe.py). Parent snapshot GETs and fixture preparation are distinct from the three observed CLI requests. Ordinary and observational scoring runs perform no financial writes.

## Services and image security

Both stacks ran on `colima-fraud-ml`, with separate Compose projects/volumes and loopback ports: Payment 18000, provider 18001, PostgreSQL 15434, ML 8002. Existing Payment/AI VM profiles were not started. The global Docker context is default.

- Payment source: `22e5fdb6709d40fc17afe697b90eeac52e086edc`; image `sha256:00a04a0c2e47db41ced6aceb7fe25dd220ad046d94580388d2b62ebcb142a472`.
- ML image: `sha256:b181fbdd368dce2f0f0c0f1fc2d5488e0ce4d16d82f7dbd9a0962bfef9dd9df0`.
- Final runtime checks confirm UID10001, read-only root/model, no capabilities, no-new-privileges, loopback publication and removed unused privileged helpers/optional vulnerable components.

The retained Trivy 0.76.1 report belongs to this exact ML image. Its raw exit remains **1/FAIL**: 44 HIGH occurrences/eight inherited Debian CVEs, zero CRITICAL. The policy was rechecked against the current container inspection and unchanged independently reviewed source digest `3412f3d4f27c59cd597248db3e880c9b497a1442d2ed2941516f077c44af0a8c`. It reports scanner_clean=false with unchanged **28 November 2026** expiry. No advisory, fix availability or expiry extension was silently accepted. This completion reused the matching immutable image scan rather than claiming a new vulnerability-database scan.

See M3-image-scan.json, M3-final-local-runtime.json and M3-final-local-image-policy.json. The earlier full-M1 HTTP smoke matched EUR/USD/JPY with max observed error 0. These local exceptions do not approve public exposure or production use.

## Independent review and publication boundary

The separate m3_review agent approved the corrected source, bounded image policy and now **local M3 acceptance**. It independently ran 62 controlled M3 tests in 5.84 s and targeted Ruff, inspected fresh 134-test evidence, and checked ordinary CLI/probe equality, fixture/model identity, original-transport forwarding, token isolation, terminal-state equality and absence of a correctness claim. It did not rerun live Payment calls or perform SQL/source edits. The ledger-page qualification above incorporates its final reporting comment. See [the review](../reviews/M3-review.md).

Recorded remote evidence for the unchanged source remains valid: source head `5e46755` passed [push CI](https://github.com/WYLLLY/fraud-detection-ml-service/actions/runs/40870726817) and [PR CI](https://github.com/WYLLLY/fraud-detection-ml-service/actions/runs/40870907218), with 134 Linux tests in 33.55 s. Documentation head `d71deb1` also passed its recorded push/PR checks. This user-requested completion runs locally: no new GitHub job, push, merge, paid API call or public deployment was initiated. The existing private PR #3 awaits publication of these new local evidence/doc changes; no current remote status is inferred from local completion.

## Reproduction and cost

See [M3_LOCAL_DEMO.md](M3_LOCAL_DEMO.md) for separation of fixture preparation from the read-only command, secure environment-token handling and exact local service URLs. ML source still has no financial database credentials or access. The recorded real-money cost is **zero**: all funds/provider outcomes are simulated and inference runs on local CPU. Results establish this one recorded local integration, not production capacity, public availability, a global ledger audit or real-fraud accuracy.

After verification, external fixture cleanup revoked its temporary session and removed the token file; this auth cleanup was not part of the scoring client. Task-owned test services and the fraud-ml VM were stopped, with volumes preserved and Docker context default. The portfolio preview remains available locally on port 3001. See M3-real-demo-cleanup.json. No Payment fixture was deleted or second payment created.
