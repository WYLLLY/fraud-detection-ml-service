# M2 acceptance matrix

M1 is merged via PR #1 (ce42db45464abcebb9bf7814accab65c361b80aa), with both final push/PR CI checks green. M2 scope is local inference only, not the Payment demo.

Behavioral Red before implementation: routes/strict schema and original-bundle HTTP parity; startup failures; safe errors/logs; bounded deterministic concurrency and release. Real integration: subprocess Uvicorn server and Docker container with a trusted mounted M1 bundle, actual HTTP health/scoring, read-only filesystem/non-root, no training invocation. Security: source/dependency/image scan, no secrets or raw inputs in responses/logs, no model upload/download endpoint. Reuse all M1 tests unchanged.

Docker setup failures are infrastructure failures, not TDD Red. No M3 code or Payment calls are authorized here.

The image policy has separate behavioral Red/Green evidence: exact reviewed exception remains explicitly non-clean; reject CRITICAL/new advisory/new version/fix available/expiry, unsafe runtime/image mismatch, malformed severity, host network, missing helpers protection, malformed or missing Debian/Python scan coverage and string-valued privilege flags. A valid complete clean scan may omit vulnerability arrays. Unit fixtures establish gate behavior; the real image scan/inspection/probe establish the current deployment evidence. No tests or scanner findings are removed to get PASS.

Database, migration, financial privilege and provider/worker tests are not applicable: this repository has no such implementation, and M2 makes no Payment request. Full model accuracy/retraining is unchanged M1 evidence; M2 tests serialization/transport parity, including the exact evaluated bundle in the container.
