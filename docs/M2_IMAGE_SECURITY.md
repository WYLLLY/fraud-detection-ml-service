# M2 image security decision

Reviewed: 29 October 2026 UTC. Expires: **28 November 2026 UTC**. Scope: local portfolio inference, no Payment integration or public deployment. This decision is a reviewed exception, **not a clean vulnerability scan or production approval**.

## Evidence and decision

The first Debian 12 image failed the unfiltered HIGH/CRITICAL Trivy gate. Moving to Python 3.12.15 slim Debian 13, applying stable security updates and removing unused privileged helpers eliminated the critical findings. The final arm64 image is `sha256:e530c4e60b33c39cd1d8b9eff04f8fbcd68d21aaf585ac57b46a10d2c1fff013`.

Trivy **0.76.1**, `--scanners vuln --severity HIGH,CRITICAL --exit-code 1`, still reports **44 HIGH package occurrences across eight CVEs, zero CRITICAL**. Raw exit code: **1 / FAIL**. Preserve [the final raw report](evidence/M2-image-scan-final.json), the earlier Bookworm/Trixie reports and [the separate policy result](evidence/M2-image-policy-result.json). No `--ignore-unfixed`, global ignore list, severity downgrade or package-database deletion is used. Package/source attribution can remain flagged after the vulnerable executable was removed.

Debian's tracker still listed these source versions as vulnerable in Trixie at review time; fixes in testing/unstable are not a supported stable update. The following reachability assessment is an inference from the advisory preconditions, source inspection and the inspected runtime; it is not proof that every possible exploit is impossible.

| Advisory/source | Preconditions and local assessment |
| --- | --- |
| [CVE-2026-76642 / util-linux](https://security-tracker.debian.org/tracker/CVE-2026-76642) | Privileged mount-hook execution. Unused mount/umount executables removed; no mount route or privileged inference process. |
| [CVE-2026-78408 / util-linux](https://security-tracker.debian.org/tracker/CVE-2026-78408) | Privileged nsenter cgroup operation. nsenter removed; no host namespace or cgroup authority. |
| [CVE-2026-78409 / util-linux](https://security-tracker.debian.org/tracker/CVE-2026-78409) | Authorized mount subdirectory traversal. Mount helpers removed; no filesystem-path input to scoring. |
| [CVE-2026-78410 / util-linux](https://security-tracker.debian.org/tracker/CVE-2026-78410) | Privileged bind-mount path race. Helpers removed, capabilities dropped, no mount execution path. |
| [CVE-2026-54369 / acl](https://security-tracker.debian.org/tracker/CVE-2026-54369) | Path-based ACL operations in a privileged caller. No ACL/path operation exposed by numeric scoring; library not observed mapped during the reviewed inference. The installed library remains affected. |
| [CVE-2025-69720 / ncurses](https://security-tracker.debian.org/tracker/CVE-2025-69720) | infocmp command overflow. The unused executable is removed; inference has no terminal-description input. |
| [CVE-2026-16742 / systemd](https://security-tracker.debian.org/tracker/CVE-2026-16742) | systemd-homed group modification. The vulnerable daemon is absent; libsystemd source-package attribution remains. |
| [CVE-2026-9538 / perl](https://security-tracker.debian.org/tracker/CVE-2026-9538) | Perl Archive::Tar processes malicious size headers. The module is absent; no upload/archive endpoint exists. |

## Enforced conditions

`configs/image-security-policy.json` lists exact CVE/package/version tuples and reasons. `scripts/image_policy.py` rejects CRITICAL, any new HIGH tuple, an available fixed version, expired exceptions, unexpected OS/image identity or missing runtime restrictions. Serving/container source hashes must match the reviewed scope. An exception refresh or source-scope update requires independent review, not just editing the hash or extending the date.

The running image must match the scanned image. Docker inspection and an in-container read-only probe establish UID 10001, zero effective capabilities, no-new-privileges, read-only root and `/models`, loopback publishing only, no privileged or host-network/PID/cgroup mode, no other host mount, no SUID/SGID executables, removed helpers and absent vulnerable optional components. See [runtime proof](evidence/M2-runtime-proof.json) and [container restrictions](evidence/M2-container-security.json).

The raw scanner status is retained separately. `ACCEPTED_REVIEWED_EXCEPTIONS` always includes `scanner_clean: false`, exact accepted IDs/count, expiry and image identity. Scanner execution/report errors fail the gate. CI publishes raw scan, policy result and runtime proof even on failure. The policy is a trusted repository check, not an attestation against a malicious runner or repository maintainer.

Do not expose this service beyond loopback, run privileged, accept untrusted bundles, add shell/archive/path operations or use this decision for another image/application. Rebuild and re-scan when stable fixes land; remove resolved tuples after review. After expiry, the affected-image CI gate fails until fixes or a fresh evidence-backed review. There is no automatic scheduled monitoring in this project.

## Reproduce

After `docker compose up --build --wait` and the documented HTTP smoke:

```sh
mkdir -p .local/trivy-cache .local/trivy-reports
rm -f .local/trivy-reports/image-scan.json
set +e
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v "$PWD/.local/trivy-cache:/root/.cache/trivy" \
  -v "$PWD/.local/trivy-reports:/reports" \
  aquasec/trivy:0.76.1 image --scanners vuln --severity HIGH,CRITICAL \
  --exit-code 1 --format json --output /reports/image-scan.json --no-progress fraud-ml:m2
scanner_status=$?
set -e
docker inspect "$(docker compose ps -q fraud)" > .local/runtime.json
docker compose exec -T fraud python - < scripts/runtime_probe.py > .local/runtime-proof.json
uv run --frozen python scripts/image_policy.py \
  --scan .local/trivy-reports/image-scan.json --runtime .local/runtime.json \
  --proof .local/runtime-proof.json --policy configs/image-security-policy.json \
  --scanner-exit-code "$scanner_status" --output .local/image-policy-result.json
```

The scanner receives the Docker socket; run only the trusted pinned scanner locally/inside disposable CI. The API container never receives that socket. On this host, use `DOCKER_CONTEXT=colima-fraud-ml` and docker-compose for the dedicated engine, and bind its actual socket for the scanner. Image IDs differ by architecture/build; compare each report with its own running container, not with this arm64 evidence ID.
