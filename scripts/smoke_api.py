"""Real loopback HTTP smoke against the exact trusted evaluated bundle."""

import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit

import httpx2
import numpy as np

from fraud_ml.bundle import load_bundle


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8002")
    parser.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args()
    url: str = args.url
    parsed = urlsplit(url)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in ("127.0.0.1", "localhost", "::1")
        or parsed.username
        or parsed.password
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Smoke is restricted to a loopback base URL")
    base = url.rstrip("/")
    bundle = load_bundle(args.bundle)
    errors: list[float] = []
    with httpx2.Client(timeout=3, trust_env=False, follow_redirects=False) as client:
        health = client.get(base + "/health")
        health.raise_for_status()
        if health.json()["model_version"] != bundle.version:
            raise RuntimeError("Health version mismatch")
        for row in [
            {"amount_minor": 1000, "currency": "EUR"},
            {"amount_minor": 12000, "currency": "USD"},
            {"amount_minor": 15000, "currency": "JPY"},
        ]:
            response = client.post(base + "/score", json=row)
            response.raise_for_status()
            result = response.json()
            expected = float(bundle.predict([row])[0])
            if (
                not isinstance(result.get("score"), (int, float))
                or not np.isfinite(result["score"])
                or abs(result["score"] - expected) > 1e-6
                or result.get("model_version") != bundle.version
                or result.get("experimental") is not True
                or result.get("training_data") != "synthetic"
            ):
                raise RuntimeError("HTTP/bundle parity failed")
            errors.append(abs(result["score"] - expected))
        if (
            client.post(base + "/score", json={"amount_minor": 1, "currency": "EUR"}).status_code
            != 422
        ):
            raise RuntimeError("Out-of-domain input accepted")
        if (
            client.post(base + "/score", json={"amount_minor": True, "currency": "EUR"}).status_code
            != 422
        ):
            raise RuntimeError("Non-strict integer accepted")
        if client.post(base + "/train").status_code != 404:
            raise RuntimeError("Unexpected training endpoint")
    print(
        json.dumps(
            {
                "health": "ok",
                "model_version": bundle.version,
                "scored": len(errors),
                "max_abs_error": max(errors),
                "validation": "strict and out-of-domain rejection verified",
            }
        )
    )


if __name__ == "__main__":
    main()
