"""Read-only local HTTP demonstration; no financial execution or training imports."""

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID

import httpx2
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from fraud_ml.domain import validate_features
from fraud_ml.schemas import ScoreResponse

CONNECT_SECONDS = 1.0
TOTAL_SECONDS = 5.0
MAX_RESPONSE_BYTES = 16_384

NOTICE = (
    "Score expérimental issu de données synthétiques ; aucune validation de fraude réelle ; "
    "aucun effet sur le paiement."
)


class DemoError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class DemoResult:
    payment_id: UUID
    prediction: ScoreResponse


class PaymentRecord(BaseModel):
    """Mirrors the existing PaymentResponse HTTP contract, without importing it."""

    model_config = ConfigDict(strict=True, extra="forbid", hide_input_in_errors=True)
    id: UUID
    wallet_id: UUID
    recipient: str = Field(min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9_.:@-]+$")
    amount_minor: int = Field(ge=1, le=10**12)
    currency: Literal["EUR", "USD", "JPY"]
    state: Literal["pending", "needs_review", "succeeded", "failed"]
    created_at: datetime
    updated_at: datetime


class HealthResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", hide_input_in_errors=True)
    status: Literal["ok"]
    model_version: str = Field(pattern=r"^[a-f0-9]{64}$")


class PeerScoreResponse(ScoreResponse):
    @field_validator("experimental", mode="before")
    @classmethod
    def explicit_experimental_marker(cls, value: object) -> Literal[True]:
        # Literal[True] alone also accepts JSON integer 1 in Pydantic.
        if value is not True:
            raise ValueError("Explicit experimental boolean required")
        return True


def _local_url(value: str) -> tuple[str, int]:
    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme not in ("http", "https")
            or parsed.hostname not in ("127.0.0.1", "localhost", "::1")
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in ("", "/")
            or "?" in value
            or "#" in value
            or any(ord(c) <= 32 or ord(c) >= 127 for c in value)
        ):
            raise ValueError
        port = parsed.port
        if port is None:
            port = 443 if parsed.scheme == "https" else 80
        if not 1 <= port <= 65535:
            raise ValueError
    except ValueError:
        raise DemoError("invalid_service_urls") from None
    return value.rstrip("/"), port


async def _fetch(
    client: httpx2.AsyncClient,
    method: str,
    url: str,
    service: str,
    *,
    headers: dict[str, str] | None = None,
    payload: dict[str, object] | None = None,
) -> bytes:
    try:
        # Encloses connection, headers and the entire streamed body, not each read.
        async with asyncio.timeout(TOTAL_SECONDS):
            async with client.stream(method, url, headers=headers, json=payload) as response:
                status = response.status_code
                if 300 <= status < 400:
                    raise DemoError(f"{service}_redirect_rejected")
                if service == "payment" and status in (401, 403):
                    raise DemoError("payment_authentication")
                if service == "payment" and status == 404:
                    raise DemoError("payment_not_found")
                if service == "fraud" and status == 422:
                    raise DemoError("fraud_rejected")
                if status != 200:
                    raise DemoError(f"{service}_unavailable")
                if (
                    response.headers.get("content-type", "").split(";", 1)[0].strip()
                    != "application/json"
                    or response.headers.get("content-encoding", "identity") != "identity"
                ):
                    raise DemoError(f"invalid_{service}_response")
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    if len(body) + len(chunk) > MAX_RESPONSE_BYTES:
                        raise DemoError(f"invalid_{service}_response")
                    body.extend(chunk)
                return bytes(body)
    except (TimeoutError, httpx2.TimeoutException):
        raise DemoError(f"{service}_timeout") from None
    except httpx2.HTTPError:
        raise DemoError(f"{service}_unavailable") from None


async def score_payment(
    payment_id: UUID,
    payment_api_url: str,
    fraud_api_url: str,
    token: str,
    *,
    payment_transport: httpx2.AsyncBaseTransport | None = None,
    fraud_transport: httpx2.AsyncBaseTransport | None = None,
) -> DemoResult:
    if not re.fullmatch(r"[A-Za-z0-9._~+/=-]+", token):
        raise DemoError("authentication_required")
    payment_base, payment_port = _local_url(payment_api_url)
    fraud_base, fraud_port = _local_url(fraud_api_url)
    # All permitted hostnames refer to loopback; avoid accidental token-to-ML routing.
    if payment_port == fraud_port:
        raise DemoError("invalid_service_urls")
    timeout = httpx2.Timeout(TOTAL_SECONDS, connect=CONNECT_SECONDS)
    payment_transport = payment_transport or httpx2.AsyncHTTPTransport(retries=0, trust_env=False)
    fraud_transport = fraud_transport or httpx2.AsyncHTTPTransport(retries=0, trust_env=False)
    async with (
        httpx2.AsyncClient(
            transport=payment_transport, timeout=timeout, follow_redirects=False, trust_env=False
        ) as payment_client,
        httpx2.AsyncClient(
            transport=fraud_transport, timeout=timeout, follow_redirects=False, trust_env=False
        ) as fraud_client,
    ):
        raw_payment = await _fetch(
            payment_client,
            "GET",
            f"{payment_base}/payments/{payment_id}",
            "payment",
            headers={"Authorization": f"Bearer {token}"},
        )
        try:
            payment = PaymentRecord.model_validate_json(raw_payment)
            if payment.id != payment_id:
                raise ValueError
        except (ValidationError, ValueError):
            raise DemoError("invalid_payment_response") from None
        features: dict[str, object] = {
            "amount_minor": payment.amount_minor,
            "currency": payment.currency,
        }
        try:
            validate_features(features)
        except ValueError:
            raise DemoError("outside_training_domain") from None
        raw_health = await _fetch(fraud_client, "GET", fraud_base + "/health", "fraud")
        try:
            health = HealthResponse.model_validate_json(raw_health)
        except ValidationError:
            raise DemoError("invalid_fraud_response") from None
        raw_score = await _fetch(
            fraud_client, "POST", fraud_base + "/score", "fraud", payload=features
        )
        try:
            prediction = PeerScoreResponse.model_validate_json(raw_score)
            if (
                prediction.model_version != health.model_version
                or prediction.model_fields_set != set(ScoreResponse.model_fields)
            ):
                raise ValueError
        except (ValidationError, ValueError):
            raise DemoError("invalid_fraud_response") from None
    return DemoResult(payment.id, prediction)
