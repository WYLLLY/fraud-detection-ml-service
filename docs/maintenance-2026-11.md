# November 2026 maintenance report

The CI workflow pins checkout, Python setup, and artifact upload to immutable GitHub Action commits. It also pins Trivy 0.76.1 to its official multi-platform image digest.

The container job rebuilds the inference image and exercises it over HTTP. Its evidence artifact contains the current raw vulnerability report, runtime proof, and the outcome of the reviewed local-only image policy. The pull request records the regression, simulation, and scan results for this change.

The local demonstration guide now identifies the public repository and the merged M3 milestone.

The November image scan identified three additional SQLite advisories. Debian Trixie has no fixed SQLite package for these advisories, and removing the library would break the base image's util-linux dependency chain. The runtime now installs the single Debian `libsqlite3-0` package at version `3.54.1-2` from Debian Snapshot, with a SHA-256 verified against the signed Debian package index for each supported architecture. The runtime probe checks that Python loads SQLite 3.54.1. The existing image policy retains its expiry and exception list.

The Trixie Trivy feed still reports the three SQLite advisories against the installed Sid build. The policy records them as verified vendor fixes only when the current image inventory matches the package name, source, and version pinned in the Dockerfile, the runtime probe confirms SQLite 3.54.1, and the report matches the reviewed advisory set. The raw report and exit code remain visible. Regression tests cover wrong runtime and package versions, unrelated advisories, a published scanner fix, and the review expiry. The existing local-only exceptions remain subject to their original controls.

Debian tracks the fixes for [CVE-2026-119373](https://security-tracker.debian.org/tracker/CVE-2026-119373), [CVE-2026-119374](https://security-tracker.debian.org/tracker/CVE-2026-119374), and [CVE-2026-119379](https://security-tracker.debian.org/tracker/CVE-2026-119379).

A follow-up regression confirms that missing runtime versions and malformed advisory lists fail closed.
