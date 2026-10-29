from copy import deepcopy
from datetime import date
from typing import Any

import pytest

from scripts.image_policy import assess


def fixture() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    scan = {
        "SchemaVersion": 2,
        "ArtifactType": "container_image",
        "Metadata": {"ImageID": "sha256:test", "OS": {"Family": "debian", "Name": "13.7"}},
        "Results": [
            {
                "Target": "image (debian 13)",
                "Class": "os-pkgs",
                "Type": "debian",
                "Packages": [{"Name": "libc6", "Version": "1"}],
                "Vulnerabilities": [
                    {
                        "VulnerabilityID": "CVE-known",
                        "PkgName": "libexample",
                        "InstalledVersion": "1",
                        "Severity": "HIGH",
                    }
                ],
            },
            {
                "Target": "Python",
                "Class": "lang-pkgs",
                "Type": "python-pkg",
                "Packages": [
                    {"Name": name, "Version": "1"}
                    for name in ("fraud-ml", "fastapi", "torch", "scikit-learn")
                ],
            },
        ],
    }
    runtime = {
        "Image": "sha256:test",
        "Config": {"User": "10001:10001"},
        "HostConfig": {
            "ReadonlyRootfs": True,
            "Privileged": False,
            "CapDrop": ["ALL"],
            "SecurityOpt": ["no-new-privileges:true"],
            "PidMode": "",
            "CgroupnsMode": "private",
            "PortBindings": {"8002/tcp": [{"HostIp": "127.0.0.1", "HostPort": "8002"}]},
        },
        "Mounts": [{"Destination": "/models", "RW": False}],
        "proof": {
            "uid": 10001,
            "cap_eff": "0000000000000000",
            "no_new_privs": 1,
            "helpers_absent": True,
            "suid_sgid_absent": True,
            "homed_absent": True,
            "archive_tar_absent": True,
        },
    }
    policy = {
        "expires": "2026-11-28",
        "exceptions": [
            {
                "id": "CVE-known",
                "package": "libexample",
                "version": "1",
                "reason": "reviewed local-only non-reachability",
            }
        ],
    }
    return scan, runtime, policy


def test_reviewed_exact_exception_is_explicit_not_a_clean_scan() -> None:
    scan, runtime, policy = fixture()
    result = assess(scan, runtime, policy, date(2026, 10, 29))
    assert result["scanner_clean"] is False
    assert result["status"] == "ACCEPTED_REVIEWED_EXCEPTIONS"
    assert result["accepted_occurrences"] == 1


@pytest.mark.parametrize(
    "change",
    [
        "critical",
        "new_cve",
        "new_version",
        "fix_available",
        "expired",
        "root",
        "writable",
        "capabilities",
        "public_port",
        "image_mismatch",
        "helper_present",
        "host_network",
        "malformed_severity",
        "string_readonly",
    ],
)
def test_unknown_or_out_of_scope_risk_is_never_accepted(change: str) -> None:
    original = fixture()
    scan, runtime, policy = deepcopy(original)
    finding = scan["Results"][0]["Vulnerabilities"][0]
    if change == "critical":
        finding["Severity"] = "CRITICAL"
    elif change == "new_cve":
        finding["VulnerabilityID"] = "CVE-new"
    elif change == "new_version":
        finding["InstalledVersion"] = "2"
    elif change == "fix_available":
        finding["FixedVersion"] = "2"
    elif change == "expired":
        policy["expires"] = "2026-10-28"
    elif change == "host_network":
        runtime["HostConfig"]["NetworkMode"] = "host"
    elif change == "malformed_severity":
        finding["Severity"] = "unexpected"
    elif change == "root":
        runtime["Config"]["User"] = "0"
    elif change == "writable":
        runtime["HostConfig"]["ReadonlyRootfs"] = False
    elif change == "string_readonly":
        runtime["HostConfig"]["ReadonlyRootfs"] = "false"
    elif change == "capabilities":
        runtime["proof"]["cap_eff"] = "0000000000000001"
    elif change == "public_port":
        runtime["HostConfig"]["PortBindings"]["8002/tcp"][0]["HostIp"] = "0.0.0.0"
    elif change == "image_mismatch":
        runtime["Image"] = "sha256:other"
    elif change == "helper_present":
        runtime["proof"]["helpers_absent"] = False
    with pytest.raises(ValueError):
        assess(scan, runtime, policy, date(2026, 10, 29))


@pytest.mark.parametrize(
    "change",
    ["empty_result", "missing_os", "missing_python", "wrong_vulnerabilities", "no_packages"],
)
def test_incomplete_scan_never_becomes_clean(change: str) -> None:
    scan, runtime, policy = fixture()
    if change == "empty_result":
        scan["Results"] = [{}]
    elif change == "missing_os":
        scan["Results"] = scan["Results"][1:]
    elif change == "missing_python":
        scan["Results"] = scan["Results"][:1]
    elif change == "wrong_vulnerabilities":
        scan["Results"][0]["Vulnerabilities"] = {}
    elif change == "no_packages":
        scan["Results"][0]["Packages"] = []
    with pytest.raises(ValueError):
        assess(scan, runtime, policy, date(2026, 10, 29))


def test_complete_clean_scan_permits_omitted_vulnerability_list() -> None:
    scan, runtime, policy = fixture()
    del scan["Results"][0]["Vulnerabilities"]
    result = assess(scan, runtime, policy, date(2026, 10, 29))
    assert result["scanner_clean"] is True
    assert result["accepted_occurrences"] == 0
