import json
import os
import subprocess
import sys
from collections.abc import Callable, Generator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

from fraud_ml.payment_demo import NOTICE

PAYMENT_ID = "00000000-0000-4000-8000-000000000123"
VERSION = "a" * 64
TOKEN = "fake-cli-token-canary"


@contextmanager
def server(
    source: Callable[[str], tuple[int, dict[str, object]]],
    journal: list[tuple[str, str, str | None, bytes]],
) -> Generator[str]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.respond()

        def do_POST(self) -> None:
            self.respond()

        def log_message(self, format: str, *args: object) -> None:
            pass

        def respond(self) -> None:
            body = self.rfile.read(int(self.headers.get("content-length", "0")))
            journal.append((self.command, self.path, self.headers.get("authorization"), body))
            status, payload = source(self.path)
            encoded = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    http = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=lambda: http.serve_forever(poll_interval=0.01), daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{http.server_port}"
    finally:
        http.shutdown()
        http.server_close()
        thread.join(timeout=3)


def payment(path: str) -> tuple[int, dict[str, object]]:
    assert path == "/payments/" + PAYMENT_ID
    return 200, {
        "id": PAYMENT_ID,
        "wallet_id": "00000000-0000-4000-8000-000000000001",
        "recipient": "fixture",
        "amount_minor": 1500,
        "currency": "EUR",
        "state": "succeeded",
        "created_at": "2026-10-29T00:00:00Z",
        "updated_at": "2026-10-29T00:01:00Z",
    }


def fraud(path: str) -> tuple[int, dict[str, object]]:
    if path == "/health":
        return 200, {"status": "ok", "model_version": VERSION}
    assert path == "/score"
    return 200, {
        "score": 0.05,
        "recommendation": "low_synthetic_risk",
        "model_version": VERSION,
        "feature_schema_version": "synthetic-risk-v1",
        "experimental": True,
        "training_data": "synthetic",
    }


def run_cli(
    payment_url: str, fraud_url: str, *, token: bool = True
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.pop("PAYMENT_API_TOKEN", None)
    if token:
        environment["PAYMENT_API_TOKEN"] = TOKEN
    environment.update(HTTP_PROXY="http://127.0.0.1:9", ALL_PROXY="http://127.0.0.1:9", NO_PROXY="")
    return subprocess.run(
        [
            sys.executable,
            "-c",
            "from fraud_ml.cli import main; raise SystemExit(main())",
            "demo",
            "--payment-id",
            PAYMENT_ID,
            "--payment-api-url",
            payment_url,
            "--fraud-api-url",
            fraud_url,
        ],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )


def test_cli_real_http_minimal_payload_safe_output_and_no_environment_proxy() -> None:
    payment_calls: list[tuple[str, str, str | None, bytes]] = []
    fraud_calls: list[tuple[str, str, str | None, bytes]] = []
    with server(payment, payment_calls) as payment_url, server(fraud, fraud_calls) as fraud_url:
        completed = run_cli(payment_url, fraud_url)
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["payment_id"] == PAYMENT_ID
    assert result["score"] == 0.05 and result["model_version"] == VERSION
    assert result["notice"] == NOTICE
    assert "label" not in result
    assert completed.stderr == ""
    assert TOKEN not in completed.stdout
    assert [(method, path) for method, path, _, _ in payment_calls] == [
        ("GET", "/payments/" + PAYMENT_ID)
    ]
    assert payment_calls[0][2] == "Bearer " + TOKEN
    assert [(method, path) for method, path, _, _ in fraud_calls] == [
        ("GET", "/health"),
        ("POST", "/score"),
    ]
    assert all(auth is None for _, _, auth, _ in fraud_calls)
    assert json.loads(fraud_calls[1][3]) == {"amount_minor": 1500, "currency": "EUR"}


def test_cli_missing_token_is_safe_and_performs_no_http() -> None:
    completed = run_cli("http://127.0.0.1:9", "http://127.0.0.1:10", token=False)
    assert completed.returncode != 0
    assert completed.stdout == ""
    assert "authentication_required" in completed.stderr
    assert "Traceback" not in completed.stderr


def test_cli_authentication_error_abstains_without_body_or_token_echo() -> None:
    calls: list[tuple[str, str, str | None, bytes]] = []
    with server(lambda _: (401, {"detail": TOKEN}), calls) as payment_url:
        completed = run_cli(payment_url, "http://127.0.0.1:10")
    assert completed.returncode != 0
    assert completed.stdout == ""
    assert "payment_authentication" in completed.stderr
    assert "Score unavailable" in completed.stderr
    assert TOKEN not in completed.stderr and "Traceback" not in completed.stderr
    assert len(calls) == 1


def test_demo_import_does_not_load_training_or_generator() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import fraud_ml.cli, fraud_ml.payment_demo, sys; "
            "assert not any(m in sys.modules for m in "
            "('fraud_ml.data','fraud_ml.training','fraud_ml.experiment','torch'))",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stderr
