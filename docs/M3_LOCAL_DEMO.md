# Run and understand the local demonstration

The original demonstration was verified on 29 October 2026. **All three milestones are implemented and merged into `main`.** [PR #3](https://github.com/WYLLLY/fraud-detection-ml-service/pull/3) integrated M3 and its verification evidence.

## What runs

The genuine Payment API, PostgreSQL, existing outbox worker and local HTTP provider simulator run separately from the genuine FastAPI ML container. The scoring CLI talks only HTTP. No hosted model, GPU service, banking connection, credit card or paid API is needed. **15 EUR is a fictional fixture amount; real money spent is zero.**

The local proof uses Payment on `http://127.0.0.1:18000` and ML on `http://127.0.0.1:8002`. These are loopback addresses on the operator's computer; a portfolio visitor cannot use that operator's localhost endpoint.

## Prepare a fixture separately

On an isolated development stack, use Projet 1's existing setup/seed tools and authenticated API to prepare a user-owned fictional payment. Keep its source, migrations and configuration untouched. The recorded run used a fresh dedicated Compose project, temporary credentials outside both repositories, opt-in fictional funding, and one separately authorized 1,500-minor-unit EUR payment. The provider simulator settled it before scoring began.

This preparation may authenticate and create test data; **fraud-ml demo does neither**. Do not run fixture preparation against production or silently interpret a scoring request as authorization to create financial operations. A later run can reuse an existing owned terminal fixture.

## Run the read-only CLI

Start the local ML service with the trusted evaluated M1 bundle, as documented in the README. Provide an owner token through the environment, without placing its value in command arguments or source files. In interactive Bash/Zsh:

```sh
read -rs PAYMENT_API_TOKEN
export PAYMENT_API_TOKEN
uv run --frozen fraud-ml demo \
  --payment-id YOUR_EXISTING_PAYMENT_UUID \
  --payment-api-url http://127.0.0.1:18000 \
  --fraud-api-url http://127.0.0.1:8002
unset PAYMENT_API_TOKEN
```

The client reads the owned payment once, validates its fields/domain, reads ML health without credentials and posts only amount_minor/currency to ML without credentials. Each call has a one-second connect timeout and a five-second absolute deadline. Invalid data or service failures mean score unavailable and nonzero exit, never zero risk. No payment creation, retry, cancellation, finalization or SQL occurs inside this command.

The recorded ordinary CLI output is [M3-real-cli.json](evidence/M3-real-cli.json): score **0.011041127797303131**, low_synthetic_risk, selected M1 model version, explicit synthetic markers and the experimental notice. That score is not a verified probability of real fraud. The payment has no known synthetic ground-truth label.

## Verify the boundary

The ordinary CLI was run first. A second read-only run used [the retained observation probe](evidence/M3-real-demo-probe.py), which forwards the original HTTP transport rather than substituting responses. For an authorized existing terminal fixture, the probe consumes `M3_PAYMENT_ID` and `PAYMENT_API_TOKEN` from the environment and writes a sanitized evidence report. Its 1,500-minor-unit EUR fixture assertions are specific to the recorded scenario.

The probe compares complete returned payment/wallet responses before and after, plus the returned ledger-history page (limit 50, offset 0). Four history entries were observed; the report does not claim a global ledger audit. The observed CLI journal contains exactly Payment GET, ML health GET and ML score POST. No bearer value, payment body, wallet balance or training label is retained in the report.

See [M3-real-demo.json](evidence/M3-real-demo.json) for state, response hashes, request methods/statuses, model/service identities and credential-isolation checks. The independent reviewer inspected these records and approved local acceptance. The 134 maintained tests separately cover controlled failures and mechanics; this one live scenario does not replace them.

## GitHub, the portfolio and a possible public demo

The GitHub repository is public. The portfolio case study presents the architecture, measured results and evidence from the local demonstration. The Payment and FastAPI services run on the operator's machine.

A proposed zero-Python-server public demo could export the selected logistic model's coefficients and preprocessing into a small browser-readable artifact, verify numerical parity with Python, and compute synthetic scores in the visitor's browser. This would exercise the evaluated model locally in the browser; FastAPI/Payment integration would remain demonstrated by the local evidence. **That interactive browser scorer is not implemented or deployed by M1–M3.** It is a separate presentation extension requiring its own tests and review.

[GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages) hosts static HTML/CSS/JavaScript, with free Pages requiring a public repository. [Vercel Hobby](https://vercel.com/docs/plans/hobby) is free for personal/non-commercial projects within its limits. These published offerings were checked on 29 October 2026; no hosting purchase or new deployment was made here. GitHub Pages does not run the Python FastAPI server. A hosted Python API needs a separately reviewed deployment and resource plan.

All public presentations must retain synthetic/experimental labeling, avoid real Payment tokens and distinguish recorded local evidence from a currently hosted service. The reviewed container exceptions do not authorize public API exposure.
