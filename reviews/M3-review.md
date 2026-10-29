# M3 independent review

Date: 29 October 2026 (Europe/Paris). Separate read-only reviewer/subagent `m3_review`, using fraud-review, fraud-api-integration and adversarial-review. Scope: M3 client/CLI, strict contracts, tests/TDD and image reachability. No source edits, live Payment calls or SQL access.

**Current final verdict: APPROVE — local M3 acceptance**, including the actual-service evidence in the final section. Earlier pending verdicts below are retained historical snapshots, superseded by the owner's subsequent fixture authorization and the successful local demonstration.

Initial result: **APPROVE WITH CHANGES** for one low defect: `parsed.port or default` accepted port zero and compared it as port 80. The implementation lane recorded D Red (1 failed/9 passed) before defaulting only when the parsed port is None. The updated URL regression asserts no request on invalid origins.

Final source result: **APPROVE**. Reviewer independently ran 61 M3 client/CLI tests in 5.91 s, then 10 corrected URL regressions in 0.11 s. Ruff and strict Pyright passed (zero errors/warnings). A/B/C/D Red/Green and full 134-case regression evidence were inspected. An initial restricted-sandbox run had two socket-permission failures; the permitted real-loopback run passed. Those environment failures are not behavioral Red.

Verified mechanisms: Payment GET only, separate clients, token restricted to that GET, distinct local service origins, no redirects/retries/environment proxies, response/identity/version checks, explicit experimental marker, bounded streamed responses, absolute five-second deadlines, generic failures and no fallback score. Demo/CLI imports do not load generator/training/torch. No financial execution path was added.

The reviewer independently approved expanded image scope including `cli.py` and `payment_demo.py`, preserving existing exception tuples and 2026-11-28 expiry. Reviewed digest: `3412f3d4f27c59cd597248db3e880c9b497a1442d2ed2941516f077c44af0a8c`. No new privileged mount/ACL/archive/terminal path was introduced. Installing the policy requires an exact match to that digest; it does not authorize a new advisory or deadline extension.

**Milestone acceptance remains incomplete** until fresh image/runtime and actual Payment+ML evidence pass. Automatic authorization review rejected the separate fixture-preparation POST; explicit owner approval or an existing authorized payment/token remains pending. Source approval neither approves Payment mutations nor substitutes for the actual demo.

Final image follow-up: **APPROVE — source and bounded local image policy**. The reviewer independently inspected the fresh Trivy report, matching Docker inspection, runtime proof and full-M1 smoke, and reran the actual policy CLI. It confirmed image b181fbdd…, exact reviewed source digest, 44 HIGH occurrences/eight CVEs/zero CRITICAL, raw exit 1, scanner_clean=false and unchanged expiry. UID10001, read-only root/model, dropped capabilities, no-new-privileges, loopback publication and absent helpers/SUID/optional vulnerable components were confirmed. There is no PAYMENT_API_TOKEN in the inference container environment. The smoke evidence was inspected, not independently rerun.

**Actual Payment acceptance remains SKIPPED**, pending the stated prerequisite. Remote CI is a separate gate. No source/image approval authorizes a Payment write or claims completion of the real demo.

## Final local acceptance after explicit fixture approval

The owner subsequently explicitly authorized one fictional 1,500-minor-unit EUR payment in the isolated local stack, with no real expenditure. The external fixture preparation and real-service evidence now supersede the earlier SKIPPED snapshots above. M3 client source remains unchanged.

Final independent verdict: **APPROVE — local M3 acceptance**. The reviewer verified that ordinary CLI output equals the observational probe output, fixture/model identities match, and the probe forwards the original transport without replacing responses. Observed client calls are exactly Payment GET, ML health GET and ML score POST; the bearer remains confined to Payment. The payment is terminal succeeded, with identical payment/wallet responses before/after, an explicit experimental notice and no fabricated label or correctness claim.

The reviewer independently reran **62 controlled M3 tests (5.84 s)** and targeted Ruff, and inspected the fresh full **134-test** regression and local quality evidence. It inspected the actual-service proof rather than making live Payment calls. A reporting qualification was incorporated: the ledger comparison concerns the returned history page (limit 50, offset 0), not a global ledger audit. No unresolved source finding remains. The bounded, explicitly non-clean image exception is unchanged. No source edits, SQL, push, merge or public deployment were performed by the reviewer.
