from copy import deepcopy
from typing import Any

import pytest

from scripts.image_policy import assess


def fixture() -> tuple[dict[str, Any], dict[str, Any]]:
    scan = {
        "SchemaVersion": 2,
        "ArtifactType": "container_image",
        "Metadata": {"ImageID": "sha256:test", "OS": {"Family": "ubuntu", "Name": "24.04"}},
        "Results": [
            {
                "Target": "image (ubuntu 24.04)",
                "Class": "os-pkgs",
                "Type": "ubuntu",
                "Packages": [
                    {"Name": name, "Version": "1"} for name in ("libc6", "libpython3.12-minimal")
                ],
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
    return scan, runtime


@pytest.mark.parametrize(
    "change",
    [
        "critical",
        "new_cve",
        "new_version",
        "fix_available",
        "wrong_os_version",
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
    scan, runtime = deepcopy(original)
    finding = scan["Results"][0]["Vulnerabilities"][0]
    if change not in {"critical", "new_cve", "new_version", "fix_available", "malformed_severity"}:
        scan["Results"][0]["Vulnerabilities"] = []
    if change == "critical":
        finding["Severity"] = "CRITICAL"
    elif change == "new_cve":
        finding["VulnerabilityID"] = "CVE-new"
    elif change == "new_version":
        finding["InstalledVersion"] = "2"
    elif change == "fix_available":
        finding["FixedVersion"] = "2"
    elif change == "wrong_os_version":
        scan["Metadata"]["OS"]["Name"] = "22.04"
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
        assess(scan, runtime)


@pytest.mark.parametrize(
    "change",
    ["empty_result", "missing_os", "missing_python", "wrong_vulnerabilities", "no_packages"],
)
def test_incomplete_scan_never_becomes_clean(change: str) -> None:
    scan, runtime = fixture()
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
        assess(scan, runtime)


def test_complete_clean_scan_permits_omitted_vulnerability_list() -> None:
    scan, runtime = fixture()
    del scan["Results"][0]["Vulnerabilities"]
    result = assess(scan, runtime)
    assert result["scanner_clean"] is True


@pytest.mark.parametrize(
    "advisory",
    ["CVE-2026-119373", "CVE-2026-119374", "CVE-2026-119379"],
)
def test_sqlite_high_result_blocks_even_with_runtime_version_proof(advisory: str) -> None:
    scan, runtime = fixture()
    scan["Results"][0]["Vulnerabilities"][0].update(
        VulnerabilityID=advisory,
        PkgName="libsqlite3-0",
        InstalledVersion="3.54.1-2",
    )
    runtime["proof"]["sqlite_version"] = "3.54.1"
    with pytest.raises(ValueError, match="HIGH"):
        assess(scan, runtime)


@pytest.mark.parametrize("name", ["libc6", "libpython3.12-minimal"])
def test_missing_native_runtime_package_blocks_clean_report(name: str) -> None:
    scan, runtime = fixture()
    scan["Results"][0].pop("Vulnerabilities")
    scan["Results"][0]["Packages"] = [
        package for package in scan["Results"][0]["Packages"] if package["Name"] != name
    ]
    with pytest.raises(ValueError, match="package coverage"):
        assess(scan, runtime)


def test_reviewed_high_still_blocks_the_release() -> None:
    scan, runtime = fixture()
    with pytest.raises(ValueError, match="HIGH"):
        assess(scan, runtime)


def test_clean_ubuntu_scan_covers_runtime_python_and_native_packages() -> None:
    scan, runtime = fixture()
    scan["Results"][0]["Vulnerabilities"] = []
    result = assess(scan, runtime)
    assert result["status"] == "PASS"
    assert result["scanner_clean"] is True
