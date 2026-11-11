"""Explicit, expiring review gate; a raw vulnerable scan never becomes clean."""

import argparse
import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, cast


def json_object(value: object) -> dict[str, Any]:
    """Narrow a JSON object at this external scanner boundary."""
    if not isinstance(value, dict):
        raise ValueError("Expected JSON object")
    return cast(dict[str, Any], value)


def scan_results(scan: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate the pinned Trivy JSON boundary before interpreting absence of findings."""
    if scan.get("SchemaVersion") != 2 or scan.get("ArtifactType") != "container_image":
        raise ValueError("Unsupported scan schema")
    raw: object = scan.get("Results")
    if not isinstance(raw, list) or not raw:
        raise ValueError("Incomplete scan")
    results: list[dict[str, Any]] = []
    coverage: set[tuple[str, str]] = set()
    for value in cast(list[object], raw):
        result = json_object(value)
        if not result.get("Target"):
            raise ValueError("Malformed scan result")
        result_class: object = result.get("Class")
        result_type: object = result.get("Type")
        if not isinstance(result_class, str) or not isinstance(result_type, str):
            raise ValueError("Malformed scan coverage")
        scope = (result_class, result_type)
        required = {
            ("os-pkgs", "debian"): {"libc6"},
            ("lang-pkgs", "python-pkg"): {"fraud-ml", "fastapi", "torch", "scikit-learn"},
        }
        if scope not in required or scope in coverage:
            raise ValueError("Unexpected or duplicated scan coverage")
        packages: object = result.get("Packages")
        if not isinstance(packages, list) or not packages:
            raise ValueError("Missing package inventory")
        names: set[str] = set()
        for entry in cast(list[object], packages):
            package = json_object(entry)
            if (
                not isinstance(package.get("Name"), str)
                or not package["Name"]
                or not isinstance(package.get("Version"), str)
                or not package["Version"]
            ):
                raise ValueError("Malformed package inventory")
            names.add(package["Name"])
        if not required[scope].issubset(names):
            raise ValueError("Incomplete package coverage")
        if "Vulnerabilities" in result and not isinstance(result["Vulnerabilities"], list):
            raise ValueError("Malformed vulnerability list")
        for entry in cast(list[object], result.get("Vulnerabilities", [])):
            finding = json_object(entry)
            if any(
                not isinstance(finding.get(key), str) or not finding[key]
                for key in ("Severity", "VulnerabilityID", "PkgName", "InstalledVersion")
            ):
                raise ValueError("Malformed vulnerability")
        coverage.add(scope)
        results.append(result)
    if coverage != {("os-pkgs", "debian"), ("lang-pkgs", "python-pkg")}:
        raise ValueError("Missing OS or Python scan coverage")
    return results


def assess(
    scan: dict[str, Any], runtime: dict[str, Any], policy: dict[str, Any], today: date
) -> dict[str, object]:
    if (
        scan["Metadata"]["OS"]["Family"] != "debian"
        or str(scan["Metadata"]["OS"]["Name"]).split(".")[0] != "13"
        or runtime["Image"] != scan["Metadata"]["ImageID"]
    ):
        raise ValueError("Image/OS identity outside reviewed scope")
    host = runtime["HostConfig"]
    if (
        runtime["Config"]["User"] != "10001:10001"
        or host["ReadonlyRootfs"] is not True
        or host["Privileged"] is not False
        or host.get("CapAdd")
        or not isinstance(host["CapDrop"], list)
        or "ALL" not in host["CapDrop"]
        or not isinstance(host["SecurityOpt"], list)
        or "no-new-privileges:true" not in host["SecurityOpt"]
        or host.get("NetworkMode") == "host"
        or host.get("PidMode") == "host"
        or host.get("CgroupnsMode") == "host"
    ):
        raise ValueError("Unsafe runtime privileges")
    bindings = host["PortBindings"]
    if (
        set(bindings) != {"8002/tcp"}
        or not bindings["8002/tcp"]
        or any(p["HostIp"] != "127.0.0.1" for p in bindings["8002/tcp"])
    ):
        raise ValueError("Runtime is not restricted to loopback")
    if not runtime["Mounts"] or any(
        m["Destination"] != "/models" or m["RW"] is not False for m in runtime["Mounts"]
    ):
        raise ValueError("Unexpected writable or host mount")
    proof = runtime["proof"]
    if (
        proof["uid"] != 10001
        or int(proof["cap_eff"], 16) != 0
        or proof["no_new_privs"] != 1
        or not all(
            proof[k] is True
            for k in ("helpers_absent", "suid_sgid_absent", "homed_absent", "archive_tar_absent")
        )
    ):
        raise ValueError("Missing mitigation proof")
    reviewed = {
        (p["id"], p["package"], p["version"]) for p in policy["exceptions"] if p.get("reason")
    }
    sqlite_fix = json_object(policy.get("verified_sqlite_fix", {}))
    sqlite_package: object = sqlite_fix.get("package_version")
    sqlite_runtime: object = sqlite_fix.get("runtime_version")
    sqlite_advisories: object = sqlite_fix.get("advisories")
    reviewed_sqlite_advisories: set[str] = set()
    if "verified_sqlite_fix" in policy:
        if (
            not isinstance(sqlite_package, str)
            or not sqlite_package.strip()
            or not isinstance(sqlite_runtime, str)
            or not sqlite_runtime.strip()
            or not isinstance(sqlite_advisories, list)
            or not sqlite_advisories
            or not all(
                isinstance(cve, str) and cve.strip()
                for cve in cast(list[object], sqlite_advisories)
            )
        ):
            raise ValueError("Incomplete verified SQLite fix configuration")
        reviewed_sqlite_advisories = set(cast(list[str], sqlite_advisories))
    valid_review = today <= date.fromisoformat(policy["expires"])
    accepted: list[str] = []
    verified_fixes: list[str] = []
    for result in scan_results(scan):
        sqlite_verified = (
            result["Type"] == "debian"
            and bool(reviewed_sqlite_advisories)
            and proof.get("sqlite_version") == sqlite_runtime
            and any(
                p["Name"] == "libsqlite3-0"
                and p.get("SrcName") == "sqlite3"
                and f"{p['Version']}-{p.get('Release')}" == sqlite_package
                for p in result["Packages"]
            )
        )
        for finding in cast(list[dict[str, Any]], result.get("Vulnerabilities", [])):
            severity = finding["Severity"]
            if severity == "CRITICAL":
                raise ValueError("CRITICAL finding cannot be exempted")
            if severity not in ("UNKNOWN", "LOW", "MEDIUM", "HIGH", "CRITICAL"):
                raise ValueError("Malformed severity")
            if severity != "HIGH":
                continue
            key = (finding["VulnerabilityID"], finding["PkgName"], finding["InstalledVersion"])
            if (
                valid_review
                and sqlite_verified
                and key[1:] == ("libsqlite3-0", sqlite_package)
                and key[0] in reviewed_sqlite_advisories
                and finding.get("Status") == "affected"
                and not finding.get("FixedVersion")
            ):
                verified_fixes.append(finding["VulnerabilityID"])
                continue
            if (
                result["Type"] != "debian"
                or key not in reviewed
                or finding.get("FixedVersion")
                or not valid_review
            ):
                raise ValueError("New, fixable, expired or unreviewed HIGH finding")
            accepted.append(finding["VulnerabilityID"])
    status = "PASS"
    if accepted:
        status = "ACCEPTED_REVIEWED_EXCEPTIONS"
    elif verified_fixes:
        status = "VERIFIED_VENDOR_FIXES"
    return {
        "status": status,
        "scanner_clean": not (accepted or verified_fixes),
        "accepted_occurrences": len(accepted),
        "accepted_cves": sorted(set(accepted)),
        "verified_vendor_fix_occurrences": len(verified_fixes),
        "verified_vendor_fix_cves": sorted(set(verified_fixes)),
        "expires": policy["expires"],
        "image": runtime["Image"],
    }


def main() -> None:
    from fraud_ml.artifact_io import digest, identity, read_json, write_json

    parser = argparse.ArgumentParser()
    for name in ("scan", "runtime", "proof", "policy", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--scanner-exit-code", type=int, required=True)
    args = parser.parse_args()
    policy = read_json(args.policy)
    sources = {name: digest(Path(name)) for name in policy["scope_files"]}
    if identity(sources) != policy["scope_sha256"]:
        raise ValueError("Code/container scope changed; independent re-review required")
    inspection = json.loads(args.runtime.read_text())
    runtime = cast(dict[str, Any], inspection[0] if isinstance(inspection, list) else inspection)
    runtime["proof"] = read_json(args.proof)
    result = assess(read_json(args.scan), runtime, policy, datetime.now(UTC).date())
    expected = 0 if result["scanner_clean"] else 1
    if args.scanner_exit_code != expected:
        raise ValueError("Scanner exit/report mismatch")
    write_json(args.output, {**result, "raw_scanner_exit_code": args.scanner_exit_code})
    print(json.dumps(result))


if __name__ == "__main__":
    main()
