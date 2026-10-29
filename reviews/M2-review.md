# M2 independent review

Date: 29 October 2026 (Europe/Paris). Separate reviewer/subagent: m2_review using fraud-review, fraud-api-integration and adversarial-review. Read-only source/test/container-configuration review; no Payment calls, edits or full experiment.

Initial verdict: APPROVE WITH CHANGES for one low acceptance-test gap: production used the correct >= comparator, but below/equal/above saved threshold were not explicitly covered.

The primary agent added test_recommendation_includes_exact_saved_threshold without altering production selection. The independent reviewer inspected and ran it: **1 passed in 2.88 s**, then returned **APPROVE**, with no remaining significant finding in the reviewed M2 code.

Independent checks before that follow-up: API suite **19 passed, 0 failures/errors/skips, 4.98 s** including the actual Uvicorn HTTP test; strict Pyright **0 errors/warnings**. A preliminary sandbox-only run had one socket-bind permission error; the same real HTTP test passed with loopback permission. That environment issue is not behavioral Red.

Inspected safeguards: strict closed schema and domains, finite bounded response, startup-only verified loading, runtime compatibility before unpickling, model/version parity, generic backend failures and safe logs, bounded semaphore with finally release, non-root/read-only/loopback Docker configuration. A fresh import confirmed no own data/training/experiment import. No financial path exists.

Container build/smoke, image vulnerability triage and final remote CI are primary-agent completion evidence, not claimed independently run by this reviewer.

## Final image and exception-policy review

The separate reviewer examined all eight Debian advisories and the hardened container's applicable preconditions. The local-only exception was considered defensible after removing unused privileged helpers and verifying UID/capability/filesystem/network restrictions. The raw scanner failure remains visible; this is not approval for public or production deployment.

The first policy review returned **REQUEST CHANGES**:

1. Medium: malformed/incomplete scan results could be labeled clean because missing/wrong vulnerability arrays were treated as empty.
2. Medium: string-valued Docker read-only flags could pass via truthiness.
3. Low: the scope hash omitted package initialization and dependency files.

The implementation lane recorded behavioral Red cycles E/F before fixing the first two. It now validates scan schema, Debian/Python package coverage, vulnerability field types and strict mitigation booleans. The scope includes `__init__.py`, `pyproject.toml` and `uv.lock`.

Final independent verdict: **APPROVE**, all three findings resolved. Reviewer independently ran **21 policy tests passed in 0.02 s**, targeted Ruff and full strict Pyright (zero errors/warnings). The actual policy CLI was also run independently against the final raw scan, inspection and runtime proof: **44 occurrences / eight CVEs accepted, scanner_clean=false**, exact image `e530c4e6…`, expiry **2026-11-28**. The scope hash and E/F Red evidence were inspected.

No reviewer source edits, Payment calls or full model retraining occurred. Remote CI status is reported separately in docs/M2_VERIFICATION.md.
