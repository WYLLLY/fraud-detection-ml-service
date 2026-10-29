# M3 acceptance matrix

Scope: read one existing owner-scoped payment over HTTP, score only amount_minor/currency, display an explicitly experimental advisory. M1/M2 are merged at 2cfcbdf. No financial execution, Payment source/config/migration changes or production deployment.

| Boundary | Required evidence |
| --- | --- |
| Input and identity | UUID/payment identity match, strict financial fields, allowed currencies and synthetic domain, closed local base URLs, missing-token abstention |
| HTTP isolation | Separate clients, bearer only on Payment GET, no retry/redirect, no environment proxy, minimal two-field ML payload |
| Response and version | Explicit synthetic/schema markers, finite bounded score, supported recommendation, model version pinned against ML health |
| Failure | 401/403/404, redirects, rate limits/5xx, malformed bodies, transport errors and no zero-risk fallback |
| Deadlines | 1 s connect and real 5 s wall-clock per HTTP call, including streamed body; deterministic cancellation regression |
| CLI | Environment-only token, safe failure and nonzero exit, payment ID/version/score/advisory notice, no raw errors or token output; training imports absent |
| Integration | Complete existing suite, controlled HTTP contracts and a separate actual local Payment+ML demo, before/after terminal record equality and GET-only payment journal |
| Quality/security | Frozen lock, Ruff/format, strict Pyright, Bandit, installed dependency audit; rebuild/scan changed image and re-review exact exception scope |

The additional ML health GET pins response identity before POST /score; it never receives the Payment token. Its own request has the same 1 s connect/5 s total bounds. This is HTTP contract validation, not another model or training operation.

Full ML retraining is not applicable: no generator/preprocessing/training changes. No new database/queue/migration/financial invariant implementation exists. The actual demo requires existing local credentials/fixtures; controlled doubles alone cannot complete it. Any dedicated fictional fixture preparation uses Projet 1's existing tools separately from the read-only demo.

Final local acceptance: PASS on 29 October 2026. The user explicitly approved one fictional local fixture, prepared outside the client. The ordinary CLI and observational probe ran against actual Payment+ML APIs; payment/wallet and the returned 50-entry ledger-history page stayed identical, with no financial write by the client. Retained evidence is M3-real-cli.json / M3-real-demo.json and the probe source. This closes the earlier real-demo prerequisite; it is separate from the 134-case controlled regression and does not claim a global ledger audit or production fraud accuracy.
