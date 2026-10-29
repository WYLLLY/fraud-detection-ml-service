# M2 verification — local inference

Date: 29 October 2026 (Europe/Paris). Status: **functional/quality/CI PASS; raw image scan FAIL with reviewed bounded local-only exceptions**. Independent review approved; M2 is ready for review and remains unmerged. No M3 Payment integration is implemented.

## M1 integration prerequisite

M1 was merged via [private PR #1](https://github.com/WYLLLY/fraud-detection-ml-service/pull/1), merge commit `ce42db45464abcebb9bf7814accab65c361b80aa`. Both final checks passed at the merged head: [push CI](https://github.com/WYLLLY/fraud-detection-ml-service/actions/runs/40831507841), [PR CI](https://github.com/WYLLLY/fraud-detection-ml-service/actions/runs/40831512567). The branch was created from synchronized main after merge. M1's initial publication snapshot is historical; this section records the confirmed merge.

## Implementation and TDD

- Strict Pydantic request/response models; no unknown fields, coercion of integer inputs or nonfinite scores.
- Startup-only trusted bundle load, metadata/hash/runtime compatibility checks before deserialization; incompatible or missing artifact prevents startup.
- Separate bounded synchronous InferenceService, one inference slot, with release in finally; FastAPI handles transport and generic safe errors.
- JSON event allowlist, no raw request/query/token/exception details. No training, download/upload or Payment endpoint.
- Non-root local Docker service, read-only root/model mount, loopback host publish and bounded CPU/memory/processes.

Cycle A: contract-only empty-route scaffold established imports; **17 behavioral failures** before implementation, then **17 passed** (M2-A-red/green.txt).
Cycle B: incompatible package metadata was accepted before the fix; the new behavioral regression failed before adding compatibility checks, then the full suite passed **49 tests** (M2-B-red/green.txt).
Real Uvicorn HTTP integration increased the suite to 50; the independent review requested explicit saved-threshold equality/below/above coverage, which was added without changing the already-correct comparator. The API and original regression then passed 51 tests.

Image-policy cycles C/D recorded 12 then 2 meaningful failures before their fixes. Independent review found incomplete scans could appear clean and string-valued Docker flags could be accepted. Cycles E/F reproduced these before implementation: **5 failed/15 passed**, then **1 failed/20 passed**, followed by **21 policy tests passed**. The reviewed source hash also includes package initialization and dependency inputs. Full final local regression: **72 passed, 0 failures, 0 errors, 0 skipped** (M2-final-tests.txt / M2-tests.xml). Test-only threshold coverage did not change the already-correct API behavior.

## Local verification

Ruff, formatting, strict Pyright and Bandit src/scripts passed. The installed-environment dependency audit passed with no known vulnerabilities and no ignored advisories. Inventories retain installed versus public advisory versions, including the official CPU torch mapping introduced in M1.

Real HTTP smoke against the mounted full M1 bundle checked EUR, USD and JPY; maximum absolute difference from original bundle prediction: **0**. Model version: `f7adeda45315d194650515fcea43bf8e71732a5a582d0cb2e8778db2746a17f2`. Runtime inspection verified UID 10001, read-only root, read-only /models, loopback publishing and healthy service. A fresh API import had no fraud_ml.data/training/experiment module. See docs/evidence/M2-container-*.json and M2-import-boundary.txt.

Initial image build on Debian 12 passed functional smoke but Trivy 0.76.1 found inherited HIGH/CRITICAL OS advisories. That scan is preserved as M2-image-scan-bookworm.json. The final image uses Debian 13 stable updates, removes unused mount/nsenter/infocmp helpers and strips SUID/SGID bits. Final raw scan: **FAIL (exit 1), zero CRITICAL, 44 HIGH occurrences / eight CVEs**. All eight have no stable fixed version at review time. The separate tested local-only policy reports **ACCEPTED_REVIEWED_EXCEPTIONS, scanner_clean=false**, expiring 28 November 2026. This is not a vulnerability-free image. Exact tuples, source hashes, runtime proof and vendor-specific reasoning are in [the image security decision](M2_IMAGE_SECURITY.md). No global advisory suppression is used.

Final hardened image: `sha256:e530c4e60b33c39cd1d8b9eff04f8fbcd68d21aaf585ac57b46a10d2c1fff013`. Real HTTP smoke against this image again matched the full evaluated M1 bundle exactly (three currencies, max error 0). See M2-image-scan-final.json, M2-image-policy-result.json, M2-runtime-proof.json and M2-container-security.json. The reviewer evaluates the exception policy independently; CI retains both the failed raw scan and separate policy decision.

### Commands and gate results

| Command/gate | Result |
| --- | --- |
| `uv sync --frozen` | PASS, locked M2 environment installed before verification |
| `uv run --frozen ruff check .` / `ruff format --check .` | PASS |
| `uv run --frozen pyright` | PASS, strict src/tests/scripts; 0 errors/warnings |
| `uv run --frozen pytest --junitxml=docs/evidence/M2-tests.xml` | PASS, 72/0/0/0 passed/failed/errors/skipped |
| `uv run --frozen bandit -r src scripts` | PASS, zero findings/suppressions |
| `uv run --frozen python scripts/audit_environment.py --output docs/evidence/M2-audited-environment.txt` then `uv run --frozen pip-audit --disable-pip --no-deps --strict -r docs/evidence/M2-audited-environment.txt` | PASS, no known dependency vulnerability; saved JSON/inventory |
| `docker --context colima-fraud-ml build -t fraud-ml:m2 .` | PASS |
| `DOCKER_CONTEXT=colima-fraud-ml docker-compose -p fraud-ml-m2 up --no-build --wait` | PASS, real healthy service |
| `uv run --frozen python scripts/smoke_api.py --bundle artifacts/m1/bundle` | PASS, exact M1 parity |
| Pinned Trivy HIGH/CRITICAL raw scan | **FAIL**, eight inherited CVEs as documented |
| `scripts/image_policy.py` with matching scan/runtime/proof/policy and raw exit 1 | **ACCEPTED_REVIEWED_EXCEPTIONS**, not a clean scan |
| `actionlint .github/workflows/ci.yml` | PASS |

Local execution used the already synchronized `.venv/bin` executables for final repeat checks (same locked environment) and persistent `.local/tools/bin/uv` for uv operations. No package upgrade or full model retraining was used to make transport tests pass.

Docker uses a dedicated Colima profile/context `fraud-ml` / `colima-fraud-ml` (2 CPUs, 4 GiB RAM, 20 GiB disk). Existing Payment/agent profiles were not started or modified. The global Docker context was restored to default; commands specify the dedicated context.

## Scope and completion limits

No full ML retraining is required for M2 transport/loader changes; unchanged model behavior is established by HTTP/bundle parity. Small test-training fixtures establish mechanics, not accuracy. M1's recorded test-set metrics/selection remain authoritative.

Remote CI includes full quality/security/regression and a Linux Docker job with a trusted tiny fixture, actual HTTP smoke and a version-pinned Trivy scan. Initial M2 push/PR verify jobs passed; container jobs failed at the original image scan. Those failures motivated the documented remediation and remain historical failures.

At reviewed application/policy head `89cb6dcee050441c073fbc3802c197733194ed00`, both [push CI](https://github.com/WYLLLY/fraud-detection-ml-service/actions/runs/40836561117) and [PR CI](https://github.com/WYLLLY/fraud-detection-ml-service/actions/runs/40836568477) completed successfully, including verify and container jobs. The image step succeeds under the explicit exception policy, not because the raw scan became clean. The following evidence-only documentation commit does not change application/policy inputs; its own CI is checked before handoff.

The downloaded PR evidence confirms Linux regression **72 passed in 29.35 s**, strict types/lint and no known Python dependency vulnerability. Its amd64 image `sha256:0cca64e83458084298d2db23b05b4174c81625305718bb80dab74ddeb2c36fe9` has the same 44/eight exception result and raw scanner exit 1; see M2-ci-image-policy-result.json and M2-ci-summary.txt. CI image identity differs from the local arm64 build as expected.

[Private PR #2](https://github.com/WYLLLY/fraud-detection-ml-service/pull/2) remains unmerged; M2 merge requires a separate user decision. No M3 work is included. After local verification the dedicated fraud-ml container/network were removed and its Colima VM stopped; the global Docker context is default. Payment profiles were not started or modified.
