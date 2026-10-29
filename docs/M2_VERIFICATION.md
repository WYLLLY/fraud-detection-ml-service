# M2 verification — local inference

Date: 29 October 2026 (Europe/Paris). Status: **implementation/local HTTP PASS; final image security and remote CI in progress**. No M3 Payment integration is implemented.

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
Real Uvicorn HTTP integration increased the suite to 50; the independent review requested explicit saved-threshold equality/below/above coverage, which was added without changing the already-correct comparator. Full final local regression: **51 passed, 0 failures, 0 errors, 0 skipped** (M2-final-tests.txt / M2-tests.xml).

## Local verification

Ruff, formatting, strict Pyright and Bandit src/scripts passed. The installed-environment dependency audit passed with no known vulnerabilities and no ignored advisories. Inventories retain installed versus public advisory versions, including the official CPU torch mapping introduced in M1.

Real HTTP smoke against the mounted full M1 bundle checked EUR, USD and JPY; maximum absolute difference from original bundle prediction: **0**. Model version: `f7adeda45315d194650515fcea43bf8e71732a5a582d0cb2e8778db2746a17f2`. Runtime inspection verified UID 10001, read-only root, read-only /models, loopback publishing and healthy service. A fresh API import had no fraud_ml.data/training/experiment module. See docs/evidence/M2-container-*.json and M2-import-boundary.txt.

Initial image build on Debian 12 passed functional smoke but Trivy 0.76.1 found inherited HIGH/CRITICAL OS advisories. That scan is preserved as M2-image-scan-bookworm.json; it is a real failed security gate, not a successful release. The image is being rebuilt on Debian 13 with current security updates, with strict scanning retained and no broad ignore policy. Final image evidence is added after scan/smoke completion.

Docker uses a dedicated Colima profile/context `fraud-ml` / `colima-fraud-ml` (2 CPUs, 4 GiB RAM, 20 GiB disk). Existing Payment/agent profiles were not started or modified. The global Docker context was restored to default; commands specify the dedicated context.

## Scope and completion limits

No full ML retraining is required for M2 transport/loader changes; unchanged model behavior is established by HTTP/bundle parity. Small test-training fixtures establish mechanics, not accuracy. M1's recorded test-set metrics/selection remain authoritative.

Remote CI includes full quality/security/regression and a Linux Docker job with a trusted tiny fixture, actual HTTP smoke and a version-pinned Trivy scan. Pending/failed checks prevent M2 completion; they are never presented as success. M2 has not been merged and no M3 work is included.
