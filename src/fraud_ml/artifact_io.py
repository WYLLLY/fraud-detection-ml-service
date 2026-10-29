"""Canonical JSON and verified local-file identities, without model loading."""

import hashlib
import json
from pathlib import Path
from typing import Any, cast


# JSON is an untyped interchange boundary; callers validate schemas before use.
def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError("Expected JSON object")
    return cast(dict[str, Any], value)


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_bytes(canonical(value) + b"\n")


def verify_files(directory: Path, expected: object) -> None:
    if not isinstance(expected, dict) or not expected:
        raise ValueError("Invalid integrity file map")
    for name, checksum in cast(dict[object, object], expected).items():
        if not isinstance(name, str) or not isinstance(checksum, str):
            raise ValueError("Invalid integrity entry")
        path = directory / name
        if (
            path.resolve().parent != directory.resolve()
            or path.is_symlink()
            or not path.is_file()
            or digest(path) != checksum
        ):
            raise ValueError("Artifact integrity check failed")
