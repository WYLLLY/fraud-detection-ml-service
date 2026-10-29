import json
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from typing import cast

import numpy as np
import pytest
from fastapi.testclient import TestClient

from fraud_ml import api
from fraud_ml.artifact_io import identity, read_json, write_json
from fraud_ml.bundle import Bundle, load_bundle
from fraud_ml.experiment import ExperimentConfig, generate_experiment, train_experiment


@pytest.fixture(scope="module")
def trained_bundle(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("api-artifact")
    data, run = root / "data", root / "run"
    generate_experiment(data, ExperimentConfig(samples=6000, epochs=2, minimum_positives=10))
    train_experiment(data, run)
    return run / "bundle"


def test_http_scores_evaluated_bundle_and_loads_it_only_once(
    trained_bundle: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected = load_bundle(trained_bundle)
    calls: list[Path] = []

    def tracked(path: Path) -> Bundle:
        calls.append(path)
        return load_bundle(path)

    monkeypatch.setattr(api, "load_bundle", tracked)
    with TestClient(api.create_app(trained_bundle)) as client:
        assert client.get("/health").status_code == 200
        for currency, amount in [("EUR", 1000), ("USD", 12000), ("JPY", 15000)]:
            response = client.post("/score", json={"amount_minor": amount, "currency": currency})
            assert response.status_code == 200
            result = response.json()
            p = expected.predict([{"amount_minor": amount, "currency": currency}])[0]
            assert result["score"] == pytest.approx(p, abs=1e-6)
            assert result["model_version"] == expected.version
            assert result["feature_schema_version"] == "synthetic-risk-v1"
            assert result["experimental"] is True and result["training_data"] == "synthetic"
            assert result["recommendation"] == (
                "elevated_synthetic_risk" if p >= expected.threshold else "low_synthetic_risk"
            )
        assert calls == [trained_bundle]


@pytest.mark.parametrize("amount", [True, "1000", 1000.0, 0, -1, 10**12 + 1, None])
def test_strict_amount_validation(trained_bundle: Path, amount: object) -> None:
    with TestClient(api.create_app(trained_bundle)) as client:
        assert (
            client.post("/score", json={"amount_minor": amount, "currency": "EUR"}).status_code
            == 422
        )


@pytest.mark.parametrize(
    "payload",
    [
        {"amount_minor": 1000, "currency": "GBP"},
        {"amount_minor": 1000},
        {"amount_minor": 1000, "currency": "EUR", "label": 1},
        [{"amount_minor": 1000, "currency": "EUR"}],
    ],
)
def test_closed_input_contract(trained_bundle: Path, payload: object) -> None:
    with TestClient(api.create_app(trained_bundle)) as client:
        assert client.post("/score", json=payload).status_code == 422


def test_domain_error_and_invalid_json_do_not_reflect_request(trained_bundle: Path) -> None:
    with TestClient(api.create_app(trained_bundle)) as client:
        response = client.post("/score", json={"amount_minor": 1, "currency": "EUR"})
        assert (
            response.status_code == 422
            and response.json()["detail"]["code"] == "outside_training_domain"
        )
        malformed = client.post(
            "/score",
            content='{"token":"secret-canary",bad}',
            headers={"Content-Type": "application/json"},
        )
        assert malformed.status_code == 422 and "secret-canary" not in malformed.text


def test_startup_rejects_missing_corrupt_or_incompatible_artifact(
    trained_bundle: Path, tmp_path: Path
) -> None:
    import shutil

    with (
        pytest.raises(RuntimeError, match="Model startup failed"),
        TestClient(api.create_app(tmp_path / "missing")),
    ):
        pass
    copied = tmp_path / "bundle"
    shutil.copytree(trained_bundle, copied)
    manifest = read_json(copied / "manifest.json")
    manifest["schema"] = "unsupported"
    manifest.pop("version")
    write_json(copied / "manifest.json", {**manifest, "version": identity(manifest)})
    with (
        pytest.raises(RuntimeError, match="Model startup failed"),
        TestClient(api.create_app(copied)),
    ):
        pass


def test_nonfinite_backend_failure_is_generic_and_log_safe(
    trained_bundle: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def bad_prediction(
        self: Bundle, rows: object
    ) -> np.ndarray[tuple[int, ...], np.dtype[np.float64]]:
        raise ValueError("secret-canary backend detail")

    monkeypatch.setattr(Bundle, "predict", bad_prediction)
    with pytest.raises(RuntimeError), TestClient(api.create_app(trained_bundle)):
        pass
    # Loading rejects the failure before requests; request-time failures are tested below.
    assert "secret-canary" not in caplog.text


def test_request_failure_and_nonfinite_score_do_not_become_zero_risk(
    trained_bundle: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    with TestClient(api.create_app(trained_bundle), raise_server_exceptions=False) as client:

        def broken(self: Bundle, rows: object) -> np.ndarray[tuple[int, ...], np.dtype[np.float64]]:
            raise ValueError("secret-canary backend detail")

        monkeypatch.setattr(Bundle, "predict", broken)
        with caplog.at_level(logging.INFO, logger="fraud_ml.api"):
            response = client.post(
                "/score",
                json={"amount_minor": 1000, "currency": "EUR"},
                headers={"Authorization": "secret-canary"},
            )
        assert response.status_code == 500 and response.json() == {
            "detail": {"code": "inference_failed"}
        }
        assert "secret-canary" not in caplog.text

        def nonfinite(
            self: Bundle, rows: object
        ) -> np.ndarray[tuple[int, ...], np.dtype[np.float64]]:
            return np.array([np.nan], dtype=np.float64)

        monkeypatch.setattr(Bundle, "predict", nonfinite)
        assert (
            client.post("/score", json={"amount_minor": 1000, "currency": "EUR"}).status_code == 500
        )
        events = [json.loads(r.message) for r in caplog.records if r.name == "fraud_ml.api"]
        assert events and all(
            set(e) <= {"route", "status", "duration_ms", "model_version", "error_code"}
            for e in events
        )


def test_concurrency_is_bounded_and_gate_released(
    trained_bundle: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    entered, release = Event(), Event()
    with TestClient(api.create_app(trained_bundle)) as client:
        original = Bundle.predict

        def slow(self: Bundle, rows: object) -> np.ndarray[tuple[int, ...], np.dtype[np.float64]]:
            entered.set()
            assert release.wait(5)
            return original(self, cast(list[dict[str, object]], rows))

        monkeypatch.setattr(Bundle, "predict", slow)
        with ThreadPoolExecutor(max_workers=2) as pool:
            future = pool.submit(
                client.post, "/score", json={"amount_minor": 1000, "currency": "EUR"}
            )
            try:
                assert entered.wait(5)
                assert (
                    client.post(
                        "/score", json={"amount_minor": 1000, "currency": "EUR"}
                    ).status_code
                    == 503
                )
            finally:
                release.set()
            assert future.result().status_code == 200
        monkeypatch.setattr(Bundle, "predict", original)
        assert (
            client.post("/score", json={"amount_minor": 1000, "currency": "EUR"}).status_code == 200
        )


def test_runtime_mismatch_is_rejected_before_unpickling(
    trained_bundle: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import shutil

    import fraud_ml.bundle as bundle_module

    copied = tmp_path / "incompatible"
    shutil.copytree(trained_bundle, copied)
    manifest = read_json(copied / "manifest.json")
    manifest["environment"]["packages"]["scikit-learn"] = "0.0.0"
    manifest.pop("version")
    write_json(copied / "manifest.json", {**manifest, "version": identity(manifest)})
    calls: list[Path] = []
    original = bundle_module.load_local

    def tracked(path: Path) -> object:
        calls.append(path)
        return original(path)

    monkeypatch.setattr(bundle_module, "load_local", tracked)
    with (
        pytest.raises(RuntimeError, match="Model startup failed"),
        TestClient(api.create_app(copied)),
    ):
        pass
    assert not calls


@pytest.mark.integration
def test_real_http_server_matches_bundle_and_redacts_logs(
    trained_bundle: Path, tmp_path: Path
) -> None:
    import os
    import socket
    import subprocess
    import sys
    import time
    import urllib.error
    import urllib.request

    expected = load_bundle(trained_bundle)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with socket.socket() as listener, (tmp_path / "server.log").open("w+") as log:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "fraud_ml.api:create_app",
                "--factory",
                "--fd",
                str(listener.fileno()),
                "--no-access-log",
                "--no-proxy-headers",
            ],
            pass_fds=(listener.fileno(),),
            stdout=log,
            stderr=log,
            env={**os.environ, "FRAUD_MODEL_DIR": str(trained_bundle)},
        )
        try:
            deadline = time.monotonic() + 30
            while True:
                try:
                    with opener.open(f"http://127.0.0.1:{port}/health", timeout=0.5) as response:
                        assert json.load(response)["model_version"] == expected.version
                    break
                except (OSError, urllib.error.URLError):
                    assert process.poll() is None and time.monotonic() < deadline
                    time.sleep(0.05)
            request = urllib.request.Request(
                f"http://127.0.0.1:{port}/score?private=secret-canary",
                data=json.dumps({"amount_minor": 1000, "currency": "EUR"}).encode(),
                headers={"Content-Type": "application/json", "Authorization": "secret-canary"},
            )
            with opener.open(request, timeout=3) as response:
                result = json.load(response)
            assert result["score"] == pytest.approx(
                expected.predict([{"amount_minor": 1000, "currency": "EUR"}])[0], abs=1e-6
            )
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        log.seek(0)
        text = log.read()
        assert "secret-canary" not in text
        assert '"route": "/score"' in text


def test_recommendation_includes_exact_saved_threshold(
    trained_bundle: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    threshold = load_bundle(trained_bundle).threshold
    assert 0 < threshold < 1
    with TestClient(api.create_app(trained_bundle)) as client:
        for probability, expected in [
            (threshold - 1e-8, "low_synthetic_risk"),
            (threshold, "elevated_synthetic_risk"),
            (threshold + 1e-8, "elevated_synthetic_risk"),
        ]:

            def controlled(
                self: Bundle, rows: object, probability: float = probability
            ) -> np.ndarray[tuple[int, ...], np.dtype[np.float64]]:
                return np.array([probability], dtype=np.float64)

            monkeypatch.setattr(Bundle, "predict", controlled)
            result = client.post("/score", json={"amount_minor": 1000, "currency": "EUR"})
            assert result.status_code == 200 and result.json()["recommendation"] == expected
