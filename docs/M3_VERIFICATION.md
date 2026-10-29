# M3 verification — read-only Payment scoring

Date: 29 October 2026 (Europe/Paris). Scope: M3 implementation on `feature/m3-payment-demo`, based on merged M2 `2cfcbdf`. **Implementation/tests PASS; actual demo SKIPPED pending fixture authorization; remote CI pending. Raw image scan FAIL with reviewed local exceptions.** M3 is incomplete and not merged.

## Architecture and contract

`payment_demo.py` owns validated local HTTP orchestration, bounded responses/deadlines and safe abstention. `cli.py` owns parsing, environment-token input and rendering; offline experiment imports are lazy. The existing M2 inference API and all training/generation code are unchanged. HTTPX2 moves from dev to runtime without changing any locked package version.

The Payment HTTP contract was re-read from Projet 1's `payments/schemas.py` and authenticated `GET /payments/{payment_id}`. No Payment internals are imported into ML. The client validates the eight existing response fields, requested UUID, strict financial values, state and dates. Only amount_minor/currency go to ML. There is no currency conversion or fabricated label.

A token-free GET /health pins model version before POST /score. Explicit experimental/schema/training markers and a finite score are mandatory; peer defaults cannot fill missing metadata. Two independent clients, loopback-only distinct ports, no redirects/retries/proxies and request-local bearer headers protect credential separation. A failed request never becomes zero risk. Logs/output omit tokens, raw errors and payment bodies.

Each call has a 1 s connection timeout and an absolute 5 s asyncio deadline enclosing headers and streamed body. Successful JSON responses are limited to 16 KiB. The blocked-body test actually runs for five seconds and observes cancellation, rather than relying on socket inactivity or a random delay.

## TDD and regressions

| Cycle | Behavioral Red | Green |
| --- | --- | --- |
| A | 56 failures against contract-only scaffold, no import/setup failure | 56 passed |
| B | Numeric `1` was accepted as the experimental boolean: 1 failed / 56 passed | Covered by subsequent 61-case combined run |
| C | CLI command absent and imports loaded training: four behavioral failures, including controlled real HTTP subprocess | 61 combined client/CLI cases passed |
| D | Independent review: port 0 reached transport; 1 failed / 9 passed, other cases deselected | 10 passed; no request on invalid URLs |

Final full regression after the review correction: **134 passed, zero failed/errors/skipped in 17.15 s**. All M1/M2 tests retained. Exact output/JUnit and Red/Green traces are in docs/evidence/M3-*. No full 60,000-row retraining was needed or performed; the selected M1 bundle remains authoritative.

Ruff and formatting PASS; strict Pyright src/tests/scripts PASS (0 errors/warnings); Bandit PASS; exact installed-environment pip-audit PASS with no known Python dependency vulnerability. Frozen offline lock/sync passed; the lock diff changes dependency placement only. Final remote CI remains pending.

## Actual demo prerequisite and current blocker

An isolated `fraud-m3-payment` Compose project was started inside the dedicated `colima-fraud-ml` VM using Projet 1's existing files read-only, fresh temporary credentials outside both repositories and separate loopback ports. Its existing opt-in seed tool prepared fictional fixture users/wallets. Existing Payment/AI Colima profiles remain stopped. The global Docker context is default.

No existing Payment token was available. Automatic authorization review **rejected the fixture-preparation POST /payments**, interpreting it as incompatible with the read-only rule. That command was not executed. Explicit owner approval for one fictional local fixture, or an existing authorized payment/token, is pending. The M3 client itself never creates a payment. Until a real demonstration succeeds, this acceptance gate is **SKIPPED / M3 incomplete**, regardless of the controlled HTTP tests.

## Independent review and remaining gates

The separate m3_review agent inspected the scoped source and A/B/C evidence, independently ran 61 M3 tests (5.91 s), Ruff and Pyright, and identified the low port-zero defect. It was fixed in the implementation lane after recorded D Red, then the entire suite was rerun. Follow-up source verdict: APPROVE, with 10 independently passed URL regressions (0.11 s) and zero type/lint errors. The reviewer independently supplied expanded source digest `3412f3d4f27c59cd597248db3e880c9b497a1442d2ed2941516f077c44af0a8c`; the policy refresh required an exact match before writing. Actual-demo acceptance remains separate.

Final image `sha256:b181fbdd368dce2f0f0c0f1fc2d5488e0ce4d16d82f7dbd9a0962bfef9dd9df0` was rebuilt with runtime HTTPX2, started with the full trusted M1 bundle, and passed real HTTP smoke (EUR/USD/JPY, max error 0). UID10001, zero capabilities, no-new-privileges, removed privileged helpers and absent vulnerable optional components are recorded in M3-runtime-proof.json. Docker inspection confirmed read-only root/model mount and loopback-only publication. No Payment token is configured for the ML service.

Fresh Trivy 0.76.1 scan: raw **FAIL/exit 1**, 44 HIGH occurrences across the same eight Debian CVEs, zero CRITICAL. The separate policy reports **ACCEPTED_REVIEWED_EXCEPTIONS, scanner_clean=false**, with unchanged tuples and 2026-11-28 expiry. No Python dependency vulnerability, new advisory, broad ignore or deadline extension was accepted. The expanded reviewed scope includes cli.py/payment_demo.py and dependency inputs. Raw scan, separate decision, runtime and smoke evidence are retained as M3-image-scan.json, M3-image-policy-result.json, M3-runtime-proof.json and M3-container-smoke.json. Final image evidence was submitted to the independent reviewer; no actual Payment acceptance is inferred from it.

## Reproducible checks

```sh
uv sync --frozen
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen pyright
uv run --frozen pytest --junitxml=docs/evidence/M3-tests.xml
uv run --frozen bandit -r src scripts
uv run --frozen python scripts/audit_environment.py --output docs/evidence/M3-audited-environment.txt
uv run --frozen pip-audit --disable-pip --no-deps --strict -r docs/evidence/M3-audited-environment.txt
docker build -t fraud-ml:m2 .
docker compose -p fraud-ml-m3 up --no-build --wait
uv run --frozen python scripts/smoke_api.py --bundle artifacts/m1/bundle
```

Local commands used the synchronized `.venv/bin` equivalents for repeated checks and persistent `.local/tools/bin/uv` with `.local/uv-cache` for frozen offline lock/sync. Docker/Compose explicitly target colima-fraud-ml. The image tag follows the existing Compose contract; M3 proof identifies the actual image digest. Scan/policy commands follow M2_IMAGE_SECURITY.md, using matching M3 scan, inspection and runtime proof.
