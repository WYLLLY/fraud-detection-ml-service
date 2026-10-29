"""Export exact installed identities plus public advisory versions; never upgrade."""

import argparse
import json
from importlib.metadata import distributions
from pathlib import Path


def advisory_version(name: str, version: str) -> str:
    # uv.lock pins the official PyTorch CPU index on Linux. Its local build suffix
    # is absent on PyPI; advisories are published against the upstream release.
    return version.removesuffix("+cpu") if name.lower() == "torch" else version


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    inventory: list[dict[str, str]] = []
    for distribution in distributions():
        name = distribution.metadata["Name"]
        if name == "fraud-ml":
            continue  # local editable application is source-reviewed, not a PyPI release
        inventory.append(
            {
                "name": name,
                "installed_version": distribution.version,
                "advisory_version": advisory_version(name, distribution.version),
            }
        )
    inventory.sort(key=lambda item: item["name"].lower())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "\n".join(f"{d['name']}=={d['advisory_version']}" for d in inventory) + "\n"
    )
    args.output.with_suffix(".json").write_text(json.dumps(inventory, indent=2) + "\n")


if __name__ == "__main__":
    main()
