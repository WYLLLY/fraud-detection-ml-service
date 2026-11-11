"""Read-only container evidence for the local image exception policy."""

import json
import os
import sqlite3
import stat
from pathlib import Path

from fraud_ml.bundle import load_bundle


def main() -> None:
    if sqlite3.sqlite_version != "3.54.1":
        raise RuntimeError("Unexpected SQLite runtime version")
    bundle = load_bundle(Path(os.environ["FRAUD_MODEL_DIR"]))
    bundle.predict([{"amount_minor": 1000, "currency": "EUR"}])
    status = dict(
        line.split(":", 1)
        for line in Path("/proc/self/status").read_text().splitlines()
        if ":" in line
    )
    elevated = False
    for root in ("/usr", "/app"):
        for parent, _, files in os.walk(root):
            for name in files:
                path = Path(parent) / name
                if path.is_file() and path.stat().st_mode & (stat.S_ISUID | stat.S_ISGID):
                    elevated = True
    helpers = ("/usr/bin/mount", "/usr/bin/umount", "/usr/bin/nsenter", "/usr/bin/infocmp")
    print(
        json.dumps(
            {
                "uid": os.getuid(),
                "sqlite_version": sqlite3.sqlite_version,
                "cap_eff": status["CapEff"].strip(),
                "no_new_privs": int(status["NoNewPrivs"]),
                "helpers_absent": all(not Path(p).exists() for p in helpers),
                "suid_sgid_absent": not elevated,
                "homed_absent": not any(Path("/usr").rglob("systemd-homed")),
                "archive_tar_absent": not any(
                    p.parent.name == "Archive" for p in Path("/usr").rglob("Tar.pm")
                ),
            }
        )
    )


if __name__ == "__main__":
    main()
