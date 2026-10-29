# M2 acceptance matrix

M1 is merged via PR #1 (ce42db45464abcebb9bf7814accab65c361b80aa), with both final push/PR CI checks green. M2 scope is local inference only, not the Payment demo.

Behavioral Red before implementation: routes/strict schema and original-bundle HTTP parity; startup failures; safe errors/logs; bounded deterministic concurrency and release. Real integration: subprocess Uvicorn server and Docker container with a trusted mounted M1 bundle, actual HTTP health/scoring, read-only filesystem/non-root, no training invocation. Security: source/dependency/image scan, no secrets or raw inputs in responses/logs, no model upload/download endpoint. Reuse all M1 tests unchanged.

Docker setup failures are infrastructure failures, not TDD Red. No M3 code or Payment calls are authorized here.
