"""Local inference application: startup-only trusted loading and safe HTTP errors."""

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

from fraud_ml.bundle import load_bundle
from fraud_ml.schemas import ScoreRequest, ScoreResponse
from fraud_ml.serving import InferenceBusy, InferenceService

__all__ = ["create_app", "load_bundle"]
logger = logging.getLogger("fraud_ml.api")


def error_response(status: int, code: str) -> JSONResponse:
    return JSONResponse(
        status_code=status, content={"detail": {"code": code}}, headers={"X-Error-Code": code}
    )


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

    @app.middleware("http")
    async def request_log(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start = perf_counter()
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        route = request.url.path if request.url.path in ("/score", "/health") else "unmatched"
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
