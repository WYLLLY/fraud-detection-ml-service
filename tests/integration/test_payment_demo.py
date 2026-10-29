import asyncio
import json
from collections.abc import AsyncIterator
from copy import deepcopy
from dataclasses import dataclass, field
from time import monotonic
from uuid import UUID

import httpx2
import pytest

from fraud_ml.payment_demo import DemoError, DemoResult, score_payment

PAYMENT_ID = UUID("00000000-0000-4000-8000-000000000123")
PAYMENT_URL = "http://127.0.0.1:18000"
FRAUD_URL = "http://127.0.0.1:18002"
TOKEN = "test-only-secret-canary"
VERSION = "a" * 64


@dataclass
class Services:
    payment: dict[str, object] = field(
        default_factory=lambda: {
            "id": str(PAYMENT_ID),
            "wallet_id": "00000000-0000-4000-8000-000000000001",
            "recipient": "local-fixture",
            "amount_minor": 1500,
            "currency": "EUR",
            "state": "succeeded",
            "created_at": "2026-10-29T00:00:00Z",
            "updated_at": "2026-10-29T00:01:00Z",
        }
    )
    health: dict[str, object] = field(
        default_factory=lambda: {"status": "ok", "model_version": VERSION}
    )
    prediction: dict[str, object] = field(
        default_factory=lambda: {
            "score": 0.05,
            "recommendation": "low_synthetic_risk",
            "model_version": VERSION,
            "feature_schema_version": "synthetic-risk-v1",
            "experimental": True,
            "training_data": "synthetic",
        }
    )
    payment_status: int = 200
    ml_status: int = 200
    health_status: int = 200
    requests: list[httpx2.Request] = field(default_factory=lambda: list[httpx2.Request]())

    async def payment_handler(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        return httpx2.Response(
            self.payment_status,
            json=self.payment,
            headers={"Location": FRAUD_URL + "/stolen-token"},
        )

    async def ml_handler(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        if request.url.path == "/health":
            return httpx2.Response(self.health_status, json=self.health)
        assert request.url.path == "/score"
        return httpx2.Response(
            self.ml_status,
            json=self.prediction,
            headers={"Location": PAYMENT_URL + "/should-not-follow"},
        )

    def run(self, *, token: str = TOKEN) -> DemoResult:
        return asyncio.run(
            score_payment(
                PAYMENT_ID,
                PAYMENT_URL,
                FRAUD_URL,
                token,
                payment_transport=httpx2.MockTransport(self.payment_handler),
                fraud_transport=httpx2.MockTransport(self.ml_handler),
            )
        )


@pytest.mark.parametrize("currency,amount", [("EUR", 1500), ("USD", 12000), ("JPY", 15000)])
def test_read_only_payload_token_isolation_and_version(currency: str, amount: int) -> None:
    services = Services()
    original = deepcopy(services.payment)
    services.payment.update(currency=currency, amount_minor=amount)
    result = services.run()
    assert result.payment_id == PAYMENT_ID
    assert result.prediction.score == 0.05
    assert result.prediction.model_version == VERSION
    assert [(r.method, r.url.path) for r in services.requests] == [
        ("GET", f"/payments/{PAYMENT_ID}"),
        ("GET", "/health"),
        ("POST", "/score"),
    ]
    payment, health, score = services.requests
    assert payment.headers["authorization"] == f"Bearer {TOKEN}"
    for request in (health, score):
        assert "authorization" not in request.headers
        assert TOKEN not in str(request.url) and TOKEN.encode() not in request.content
    assert json.loads(score.content) == {"amount_minor": amount, "currency": currency}
    assert original["state"] == services.payment["state"]
    for request in services.requests:
        assert request.extensions["timeout"] == {
            "connect": 1.0,
            "read": 5.0,
            "write": 5.0,
            "pool": 5.0,
        }


@pytest.mark.parametrize("token", ["", " ", "with\nnewline", "with space"])
def test_missing_or_invalid_token_stops_before_network(token: str) -> None:
    services = Services()
    with pytest.raises(DemoError, match="authentication_required"):
        services.run(token=token)
    assert not services.requests


@pytest.mark.parametrize(
    "payment_url,fraud_url",
    [
        ("http://example.com", FRAUD_URL),
        ("http://user:secret@127.0.0.1:18000", FRAUD_URL),
        (PAYMENT_URL + "/prefix", FRAUD_URL),
        (PAYMENT_URL + "?secret=1", FRAUD_URL),
        (PAYMENT_URL + "#fragment", FRAUD_URL),
        (PAYMENT_URL, PAYMENT_URL),
        (PAYMENT_URL, "http://localhost:18000"),
        (PAYMENT_URL, "file:///tmp/model"),
        ("http://127.0.0.1:99999", FRAUD_URL),
        ("http://127.0.0.1:0", FRAUD_URL),
    ],
)
def test_only_distinct_local_service_origins(payment_url: str, fraud_url: str) -> None:
    services = Services()
    with pytest.raises(DemoError, match="invalid_service_urls"):
        asyncio.run(
            score_payment(
                PAYMENT_ID,
                payment_url,
                fraud_url,
                TOKEN,
                payment_transport=httpx2.MockTransport(services.payment_handler),
                fraud_transport=httpx2.MockTransport(services.ml_handler),
            )
        )
    assert not services.requests


@pytest.mark.parametrize(
    "status,code",
    [
        (401, "payment_authentication"),
        (403, "payment_authentication"),
        (404, "payment_not_found"),
        (429, "payment_unavailable"),
        (500, "payment_unavailable"),
        (302, "payment_redirect_rejected"),
    ],
)
def test_payment_failures_never_score_or_retry(status: int, code: str) -> None:
    services = Services(payment_status=status)
    with pytest.raises(DemoError, match=code):
        services.run()
    assert len(services.requests) == 1


@pytest.mark.parametrize(
    "key,value",
    [
        ("id", str(UUID(int=0))),
        ("amount_minor", True),
        ("amount_minor", 1500.0),
        ("amount_minor", "1500"),
        ("amount_minor", 0),
        ("amount_minor", 10**12 + 1),
        ("currency", "GBP"),
        ("state", "created"),
        ("wallet_id", "not-a-uuid"),
        ("created_at", "not-a-date"),
    ],
)
def test_incompatible_payment_is_never_forwarded(key: str, value: object) -> None:
    services = Services()
    services.payment[key] = value
    with pytest.raises(DemoError, match="invalid_payment_response"):
        services.run()
    assert len(services.requests) == 1


def test_outside_synthetic_domain_is_explicit_abstention() -> None:
    services = Services()
    services.payment["amount_minor"] = 1
    with pytest.raises(DemoError, match="outside_training_domain"):
        services.run()
    assert len(services.requests) == 1


@pytest.mark.parametrize("status", [301, 307, 422, 500, 503])
def test_ml_failure_or_redirect_has_no_score_and_no_retry(status: int) -> None:
    services = Services(ml_status=status)
    with pytest.raises(DemoError, match="fraud_"):
        services.run()
    assert len(services.requests) == 3


@pytest.mark.parametrize(
    "key,value",
    [
        ("score", float("nan")),
        ("score", float("inf")),
        ("score", -0.01),
        ("score", 1.01),
        ("score", False),
        ("score", "0.05"),
        ("model_version", "b" * 64),
        ("model_version", "unknown"),
        ("experimental", False),
        ("training_data", "real"),
        ("feature_schema_version", "future-v2"),
        ("recommendation", "approve_payment"),
    ],
)
def test_incompatible_ml_response_is_never_a_valid_score(key: str, value: object) -> None:
    services = Services()
    services.prediction[key] = value

    # Response(content=...) deliberately permits nonstandard NaN JSON as a hostile peer.
    async def handler(request: httpx2.Request) -> httpx2.Response:
        services.requests.append(request)
        body = services.health if request.url.path == "/health" else services.prediction
        return httpx2.Response(
            200, content=json.dumps(body), headers={"content-type": "application/json"}
        )

    with pytest.raises(DemoError, match="invalid_fraud_response"):
        asyncio.run(
            score_payment(
                PAYMENT_ID,
                PAYMENT_URL,
                FRAUD_URL,
                TOKEN,
                payment_transport=httpx2.MockTransport(services.payment_handler),
                fraud_transport=httpx2.MockTransport(handler),
            )
        )


@pytest.mark.parametrize("key", ["experimental", "training_data", "feature_schema_version"])
def test_metadata_defaults_must_not_hide_missing_peer_fields(key: str) -> None:
    services = Services()
    del services.prediction[key]
    with pytest.raises(DemoError, match="invalid_fraud_response"):
        services.run()


def test_health_version_is_required_before_scoring() -> None:
    services = Services(health={"status": "ok", "model_version": "unknown"})
    with pytest.raises(DemoError, match="invalid_fraud_response"):
        services.run()
    assert len(services.requests) == 2


def test_transport_failure_is_safe_and_does_not_retry() -> None:
    calls: list[str] = []

    async def failed(request: httpx2.Request) -> httpx2.Response:
        calls.append(request.url.path)
        raise httpx2.ConnectError(TOKEN, request=request)

    with pytest.raises(DemoError, match="payment_unavailable") as error:
        asyncio.run(
            score_payment(
                PAYMENT_ID,
                PAYMENT_URL,
                FRAUD_URL,
                TOKEN,
                payment_transport=httpx2.MockTransport(failed),
            )
        )
    assert TOKEN not in str(error.value)
    assert len(calls) == 1


def test_total_deadline_cancels_response_body_not_just_socket_inactivity() -> None:
    closed: list[bool] = []

    class BlockedBody(httpx2.AsyncByteStream):
        async def __aiter__(self) -> AsyncIterator[bytes]:
            try:
                yield b"{"
                await asyncio.Event().wait()
            finally:
                closed.append(True)

    async def slow(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200, stream=BlockedBody(), headers={"content-type": "application/json"}
        )

    started = monotonic()
    with pytest.raises(DemoError, match="payment_timeout"):
        asyncio.run(
            score_payment(
                PAYMENT_ID,
                PAYMENT_URL,
                FRAUD_URL,
                TOKEN,
                payment_transport=httpx2.MockTransport(slow),
            )
        )
    assert closed == [True]
    assert monotonic() - started < 8


def test_numeric_true_is_not_an_explicit_experimental_marker() -> None:
    services = Services()
    services.prediction["experimental"] = 1
    with pytest.raises(DemoError, match="invalid_fraud_response"):
        services.run()
