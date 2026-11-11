# November 2026 maintenance report

The CI workflow pins checkout, Python setup, and artifact upload to immutable GitHub Action commits. It also pins Trivy 0.76.1 to its official multi-platform image digest.

The container job rebuilds the inference image and exercises it over HTTP. Its evidence artifact contains the current raw vulnerability report, runtime proof, and the outcome of the reviewed local-only image policy. The pull request records the regression, simulation, and scan results for this change.
