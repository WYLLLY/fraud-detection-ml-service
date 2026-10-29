---
name: fraud-api-integration
description: Build or review Fraud ML M2 FastAPI inference and M3 read-only Payment HTTP demo, including validation, artifact trust, errors and secret isolation; not financial execution.
---

# Fraud API Integration

Read AGENTS.md and the authorized M2 or M3 contract. For M2 inspect the trusted M1 bundle; for M3 recheck the actual Payment response schema in read-only mode before relying on old audit evidence.

## M2 inference

- POST /score accepts only strict integer amount_minor and allowed currency. Reject booleans, coerced strings/floats, extras and values outside financial or saved synthetic bounds; distinguish outside_training_domain. No fallback score.
- GET /health is available only after valid startup. Verify bundle identity/hash/schema/shape, preload once, and fail startup on missing/corrupt/incompatible artifacts. No training imports, p(x), arbitrary model paths from requests, uploads or hot reload.
- Execute saved preprocessing/model/threshold together. Validate finite bounded score, exact schema/model version, experimental marker and synthetic training origin. Indicators have no financial authority.
- Keep CPU work off an unconstrained async task path; use the single-process bounded MVP design. Docker binds host loopback, runs non-root and mounts a trusted bundle read-only. Generic errors and allowlisted logs contain no request payload or secrets.

## M3 demo

- CLI reads one existing user-owned payment through authenticated GET, forwards only amount_minor/currency to ML, and prints advisory output with the plan's experimental notice. No write request, SQL, creation, login automation, cancellation or financial retry.
- Use separate client/header scopes: PAYMENT_API_TOKEN belongs only to Payment, never ML. Environment token only; no command-line secret or logging. Redirects/retries are disabled; implement a 1 s connection timeout and a real 5 s wall-clock deadline per call, not just socket inactivity.
- Handle missing token, 401/403/404, incompatible Payment data, out-of-domain ML response, connect/timeouts and 5xx with score unavailable and nonzero exit. Reject nonfinite/mismatched ML response metadata.
- Real demo uses an existing authorized fixture, preferably a terminal payment. A pending state may evolve through the existing worker, so do not infer causation from before/after difference alone. No label or oracle probability is attached to that payment.

Tests cover strictness, boundaries/threshold, artifact failures, real HTTP inference parity, token separation and deadline/error behavior. Controlled Payment HTTP doubles establish contracts only; M3 acceptance separately requires real Payment+ML evidence. Record missing prerequisites instead of claiming E2E success.
