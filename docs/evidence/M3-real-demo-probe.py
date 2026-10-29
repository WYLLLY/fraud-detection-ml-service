"""Opt-in evidence probe, not product code or a CI fake; never creates a payment.

Requires an existing terminal fixture and PAYMENT_API_TOKEN from the environment.
The observational transport wrapper forwards to real HTTP without replacing data.
Parent snapshot GETs are separate from the three observed CLI requests.
"""

import contextlib
import hashlib
import io
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx2

from fraud_ml.cli import main
from fraud_ml.payment_demo import NOTICE, PaymentRecord


def main_probe() -> None:
    payment_id = os.environ["M3_PAYMENT_ID"]
    token = os.environ["PAYMENT_API_TOKEN"]
    payment_url = "http://127.0.0.1:18000"
    fraud_url = "http://127.0.0.1:8002"
    headers = {"Authorization": "Bearer " + token}
    journal: list[dict[str, object]] = []
    original = httpx2.AsyncHTTPTransport.handle_async_request

    async def observed(
        transport: httpx2.AsyncHTTPTransport, request: httpx2.Request
    ) -> httpx2.Response:
        body = await request.aread()
        if request.url.port == 18000:
            assert request.method == "GET"
            assert request.url.path == "/payments/" + payment_id
            assert request.headers.get("authorization") == headers["Authorization"]
            route, service = "/payments/{payment_id}", "payment"
        else:
            assert request.url.port == 8002
            assert "authorization" not in request.headers
            assert token not in str(request.url) and token.encode() not in body
            route, service = request.url.path, "fraud"
            if route == "/score":
                assert request.method == "POST"
                assert json.loads(body) == {"amount_minor": 1500, "currency": "EUR"}
            else:
                assert route == "/health" and request.method == "GET"
        response = await original(transport, request)
        journal.append(
            {
                "service": service,
                "method": request.method,
                "route": route,
                "status": response.status_code,
            }
        )
        return response

    with httpx2.Client(timeout=3, trust_env=False, follow_redirects=False) as client:
        before = client.get(payment_url + "/payments/" + payment_id, headers=headers)
        before.raise_for_status()
        record = PaymentRecord.model_validate_json(before.content)
        assert record.state in ("succeeded", "failed")
        wallet_path = f"/wallets/{record.wallet_id}"
        wallet_before = client.get(payment_url + wallet_path, headers=headers)
        ledger_before = client.get(payment_url + wallet_path + "/ledger", headers=headers)
        wallet_before.raise_for_status()
        ledger_before.raise_for_status()
        captured, errors = io.StringIO(), io.StringIO()
        sys.argv = [
            "fraud-ml",
            "demo",
            "--payment-id",
            payment_id,
            "--payment-api-url",
            payment_url,
            "--fraud-api-url",
            fraud_url,
        ]
        httpx2.AsyncHTTPTransport.handle_async_request = observed
        try:
            with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(errors):
                exit_code = main()
        finally:
            httpx2.AsyncHTTPTransport.handle_async_request = original
        assert exit_code == 0 and not errors.getvalue()
        assert token not in captured.getvalue()
        result = json.loads(captured.getvalue())
        assert result["payment_id"] == payment_id and result["notice"] == NOTICE
        assert result["experimental"] is True and result["training_data"] == "synthetic"
        manifest = json.loads(Path("artifacts/m1/bundle/manifest.json").read_text())
        assert result["model_version"] == manifest["version"]
        assert not any(
            name in sys.modules
            for name in ("fraud_ml.data", "fraud_ml.training", "fraud_ml.experiment", "torch")
        )
        assert [(r["service"], r["method"], r["route"]) for r in journal] == [
            ("payment", "GET", "/payments/{payment_id}"),
            ("fraud", "GET", "/health"),
            ("fraud", "POST", "/score"),
        ]
        after = client.get(payment_url + "/payments/" + payment_id, headers=headers)
        wallet_after = client.get(payment_url + wallet_path, headers=headers)
        ledger_after = client.get(payment_url + wallet_path + "/ledger", headers=headers)
        for response in (after, wallet_after, ledger_after):
            response.raise_for_status()
        assert before.content == after.content
        assert wallet_before.content == wallet_after.content
        assert ledger_before.content == ledger_after.content

    proof = {
        "status": "PASS",
        "recorded_at": datetime.now(UTC).isoformat(),
        "real_services": True,
        "provider": "local simulator",
        "real_money_spent": 0,
        "source_revision": "d71deb1f79013a822e33a3ddcc6399ab1ffc84bf",
        "observational_probe": "forwards real transport; no mocked response",
        "payment_state_before": record.state,
        "payment_state_after": record.state,
        "payment_unchanged": True,
        "wallet_unchanged": True,
        "returned_ledger_history_unchanged": True,
        "ledger_history_limit": 50,
        "ledger_history_offset": 0,
        "ledger_history_entries_seen": len(ledger_before.json()),
        "payment_sha256": hashlib.sha256(before.content).hexdigest(),
        "wallet_sha256": hashlib.sha256(wallet_before.content).hexdigest(),
        "ledger_sha256": hashlib.sha256(ledger_before.content).hexdigest(),
        "token_isolated": True,
        "no_training_or_generator_import": True,
        "cli_exit_code": exit_code,
        "cli_requests": journal,
        "cli_output": result,
        "correctness_claim": "No real-fraud or synthetic ground-truth label for this payment",
    }
    Path("docs/evidence/M3-real-demo.json").write_text(
        json.dumps(proof, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "score": result["score"],
                "state": record.state,
                "payment_wallet_returned_history_unchanged": True,
                "real_money_spent": 0,
                "requests": journal,
            }
        )
    )


if __name__ == "__main__":
    main_probe()
