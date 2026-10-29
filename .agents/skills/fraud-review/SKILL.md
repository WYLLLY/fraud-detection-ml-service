---
name: fraud-review
description: Independently review Fraud ML milestones or agent instructions for leakage, PyTorch errors, unsafe inference, test evidence and Payment boundary violations; read-only, no fixes or implementation.
---

# Fraud Independent Review

Read AGENTS.md and the accepted plan. Reuse installed adversarial-review for generic finding structure and evidence quality, applying only relevant mechanisms. For implemented milestones the reviewer must be independent of the implementation author; a self-check is not an independent verdict. Instructions-only setup may use this workflow as a read-only discovery/behavior probe without inventing implementation evidence.

Inspect the scoped patch/artifacts and tests, not just the author's report:

- M1: split row identity and fit lineage, reference/label isolation, generator not tuned to winner, identical preprocessing, logit/loss/shape correctness, validation-only early stop/model/threshold choice, immutable best checkpoint, honest calibration/undefined metrics and sealed final test.
- M2: artifact provenance versus checksum alone, trusted deserialization, validation strictness/domain/threshold/version, startup failure, actual API/bundle parity, bounded local serving and redacted logs.
- M3: GET-only owned payment access, no shared token headers/redirect leak, real total deadline, error abstention, real integration evidence separate from doubles, no invented payment label or financial effect.
- Every milestone: behavioral pre-implementation Red, no weakened regressions, actual Ruff/Pyright/pytest/security results, docs and acceptance alignment, no infrastructure expansion.
- Guidance setup: descriptions select the right local skills, existing generic skills are reused without copies, all referenced paths resolve, newer user constraints override obsolete plan tooling, and a fresh Codex process can discover/use the guidance. Static YAML checks do not alone prove model behavior.

Construct concrete failure scenarios without modifying application files or touching live Payment data. Report severity, precise location, trigger, impact, evidence, existing coverage and required regression. Separate confirmed defects from questions or unexecuted probes. Give APPROVE / APPROVE WITH CHANGES / REQUEST CHANGES plus verification limitations; do not mark absent code or skipped app tests as successful implementation. Do not fix findings, merge or start the next milestone.
