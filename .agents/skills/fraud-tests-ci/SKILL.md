---
name: fraud-tests-ci
description: Verify Fraud ML TDD, complete pytest regression, strict Pyright, Ruff, security scans and milestone-specific HTTP/Docker integration; not a generic replacement for verification.
---

# Fraud Tests and CI

Read AGENTS.md, the current milestone and its acceptance criteria. Reuse the installed verification skill for the generic Red/evidence/full-regression gate; this skill supplies the ML-specific test matrix and commands. PostgreSQL/Redis/migrations are not required here because no such implementation exists.

1. Inventory current tooling/tests before running commands. Missing code/tools during instruction-only setup are NOT IMPLEMENTED/SKIPPED, never proof of successful application checks. Do not bootstrap M1 just to verify guidance.
2. Map changed behavior to meaningful unit, integration, API, security and failure assertions. Record a behavioral Red before application changes. Preserve evidence and test coverage through Green and Refactor.
3. Run frozen installation, Ruff check and format-check, strict Pyright over src/tests, targeted tests and the full pytest suite after implementation and review corrections. Use repo-configured commands; never weaken diagnostics/test assertions for PASS.
4. Run locked pip-audit and Bandit checks specified in AGENTS.md. Audit the actual locked environment without upgrades. At M2 build/scan the image and run real HTTP smoke with a trusted tiny test bundle. Report scan scope, findings and failures, including offline vulnerability-service failures.
5. PR CI uses deterministic small training fixtures for both frameworks and no Payment credentials, private repo fetch, full experiment or artifact upload from untrusted sources. A small-fixture pass is mechanics evidence only.
6. Full 60,000-row experiment is explicit M1 work. Reuse recorded results for API-only changes; rerun when generator/features/training changes. Verify parity against the same evaluated bundle.
7. M3 contract tests exercise fake HTTP failures plus a separate real local demo. Missing services/credentials leave that acceptance gate incomplete. No actual payment mutation or full Projet 1 financial suite is introduced by this repository.

For deadlines use deterministic synchronization or injected clocks where possible; avoid flaky random sleeps. State which tests use doubles and which cross real HTTP/container boundaries. No invented load, accuracy or security guarantees.

Report exact commands, TDD evidence, unit/integration/API/security results, passed/failed/errors/skipped counts, unresolved findings and PASS/FAIL/SKIPPED per required gate. A required skipped check prevents milestone completion. Guidance-only validation is a separate result from application verification.
