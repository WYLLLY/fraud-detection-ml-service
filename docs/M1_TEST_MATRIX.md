# M1 acceptance and TDD matrix

Scope: data, sklearn and CPU MLP, evaluation, trusted bundle, CLI and CI only.

| Gate | Behavioral tests planned |
| --- | --- |
| Data | Formula/domain, deterministic seeds, separate oracle, integer currency validation, disjoint persisted row IDs/class support |
| Leakage | Closed feature schema, train-only scaler statistics, immutable saved partitions and no oracle in learned inputs |
| PyTorch | Parameter updates, validation does not mutate state, checkpoint copy, deterministic tiny run, logits/target shape |
| Evaluation | Known metrics, AP vs trapezoidal PR-AUC, undefined values, threshold ties, strict validation selection margin, calibration counts |
| Bundle/security | Hash and metadata/schema/shape verification before trusted deserialization, path escape rejection, finite score and reload parity |
| Integration | Actual training for both frameworks, CLI generate/train/evaluate, frozen candidate decisions before test, JSON/plots and bundle round trip |
| Quality | Ruff, format, strict Pyright, full pytest, Bandit, actual-environment dependency audit |

API/Docker/Payment integration: not applicable to M1; M2/M3 are not implemented.
Each cycle's actual pre-implementation Red and subsequent Green logs are kept under docs/evidence.
Contract-only stubs may establish importable interfaces; import/setup failures are not counted as Red.
