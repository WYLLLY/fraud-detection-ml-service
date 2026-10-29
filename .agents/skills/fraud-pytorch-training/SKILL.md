---
name: fraud-pytorch-training
description: Implement or inspect the CPU PyTorch MLP, loss, training loop and checkpoint handling for Fraud ML M1; use the data and evaluation skills for their separate responsibilities.
---

# Fraud PyTorch Training

Read AGENTS.md and the M1 model specification. Consume the saved four-input preprocessing and split IDs from the data pipeline; do not infer features or refit scaling.

- Implement the exact 4-16-8-1 nn.Module with ReLU and final logit. BCEWithLogitsLoss consumes logits and matching float targets, never an already-sigmoided probability. Check shapes to prevent silent broadcasting.
- Use the plan's Adam/LR/batch/epoch/patience/seed configuration. Seed Python/NumPy/torch and shuffling; record threads, device, dtype and deterministic settings. CPU is the default; do not silently switch to MPS/CUDA.
- Separate train mode and validation eval/inference mode. Reset gradients each batch, backpropagate and step optimizer; validation must not update weights or scaler statistics. Stop and diagnose nonfinite loss/predictions.
- Early-stop on validation AP only. Save an actual copy/serialized best state_dict, not a live alias; restore that checkpoint before evaluation/export. Never use test data for checkpoint or seed selection.
- Save architecture/config/state_dict and transform identity. Load only trusted tensors with weights_only=True, CPU mapping and strict shape/key checks; call eval before inference. Optimizer state for resuming is not required by this MVP.

Write meaningful Red tests before the loop: parameters change on a deterministic learnable tiny fixture, validation leaves parameters unchanged, a later optimizer step does not mutate the saved best checkpoint, and export/reload preserves predictions within the plan tolerance. A tiny training smoke checks mechanics, not full-dataset quality. Do not force a superiority claim over logistic regression.

Return checkpoint lineage, loss/validation history, seed/environment and test evidence. Selection, threshold and final-test access belong to fraud-model-evaluation.
