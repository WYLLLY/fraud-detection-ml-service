"""Local inference application: startup-only trusted loading and safe HTTP errors."""

import asyncio
import json
import logging
import os
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter

import torch
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette._utils import get_route_path
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from fraud_ml.bundle import load_bundle
from fraud_ml.schemas import ScoreRequest, ScoreResponse
from fraud_ml.serving import InferenceBusy, InferenceService

__all__ = ["create_app", "load_bundle"]
MAX_SCORE_BODY_BYTES = 1024
MAX_PENDING_SCORES = 8
SCORE_BODY_TIMEOUT_SECONDS = 2.0

logger = logging.getLogger("fraud_ml.api")


def error_response(status: int, code: str) -> JSONResponse:
    return JSONResponse(
        status_code=status, content={"detail": {"code": code}}, headers={"X-Error-Code": code}
    )


class ScoreAdmission:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.pending = 0

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] != "http"
            or scope["method"] != "POST"
            or get_route_path(scope) != "/score"
        ):
            await self.app(scope, receive, send)
            return

        # The single ASGI worker owns this counter. Admission never waits for a slot.
        if self.pending >= MAX_PENDING_SCORES:
            await error_response(503, "score_capacity_exceeded")(scope, receive, send)
            return

        self.pending += 1
        try:
            body = bytearray()
            try:
                async with asyncio.timeout(SCORE_BODY_TIMEOUT_SECONDS):
                    while True:
                        message = await receive()
                        if message["type"] == "http.disconnect":
                            await error_response(400, "request_incomplete")(scope, receive, send)
                            return
                        chunk = message.get("body", b"")
                        if len(body) + len(chunk) > MAX_SCORE_BODY_BYTES:
                            await error_response(413, "request_too_large")(scope, receive, send)
                            return
                        body.extend(chunk)
                        if not message.get("more_body", False):
                            break
            except TimeoutError:
                await error_response(408, "request_body_timeout")(scope, receive, send)
                return

            buffered: bytes | None = bytes(body)

            async def replay_body() -> Message:
                nonlocal buffered
                if buffered is None:
                    return await receive()
                message: Message = {"type": "http.request", "body": buffered, "more_body": False}
                buffered = None
                return message

            await self.app(scope, replay_body, send)
        finally:
            self.pending -= 1


def create_app(bundle_dir: Path | None = None) -> FastAPI:
    if not any(handler.name == "fraud-json" for handler in logger.handlers):
        handler = logging.StreamHandler()
        handler.name = "fraud-json"
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    directory = bundle_dir or Path(os.environ.get("FRAUD_MODEL_DIR", "artifacts/m1/bundle"))
    service: InferenceService | None = None

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        nonlocal service
        try:
            torch.set_num_threads(1)
            service = InferenceService(load_bundle(directory))
        except Exception:
            raise RuntimeError("Model startup failed") from None
        yield
        service = None

    app = FastAPI(
        title="Experimental Synthetic Risk", lifespan=lifespan, docs_url=None, redoc_url=None
    )

    app.add_middleware(ScoreAdmission)

    @app.middleware("http")
    async def request_log(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start = perf_counter()
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        path = get_route_path(request.scope)
        route = path if path in ("/score", "/health") else "unmatched"
        logger.info(
            json.dumps(
                {
                    "route": route,
                    "status": response.status_code,
                    "duration_ms": round((perf_counter() - start) * 1000, 3),
                    "model_version": service.bundle.version if service else None,
                    "error_code": response.headers.get("X-Error-Code"),
                },
                allow_nan=False,
            )
        )
        return response

    @app.exception_handler(RequestValidationError)
    async def invalid_input(request: Request, error: RequestValidationError) -> JSONResponse:
        return error_response(422, "invalid_request")

    @app.get("/health")
    def health() -> JSONResponse:
        if service is None:
            return error_response(503, "model_unavailable")
        return JSONResponse({"status": "ok", "model_version": service.bundle.version})

    @app.post("/score", response_model=ScoreResponse)
    def score(request: ScoreRequest) -> ScoreResponse | JSONResponse:
        if service is None:
            return error_response(503, "model_unavailable")
        # Domain errors are separated from backend failures; a model ValueError is
        # never interpreted as a harmless invalid user input or a zero risk score.
        from fraud_ml.domain import validate_features

        try:
            validate_features(request.model_dump())
        except ValueError:
            return error_response(422, "outside_training_domain")
        try:
            return service.score(request)
        except InferenceBusy:
            return error_response(503, "inference_busy")
        except Exception:
            return error_response(500, "inference_failed")

    return app
