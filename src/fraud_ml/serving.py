"""Synchronous bounded inference; no generation, optimization or HTTP concerns."""

from threading import BoundedSemaphore

from fraud_ml.bundle import Bundle
from fraud_ml.domain import validate_features
from fraud_ml.schemas import ScoreRequest, ScoreResponse


class InferenceBusy(Exception):
    """The single in-flight inference slot is occupied."""


class InferenceService:
    def __init__(self, bundle: Bundle) -> None:
        self.bundle = bundle
        self._slot = BoundedSemaphore(1)

    def score(self, request: ScoreRequest) -> ScoreResponse:
        row: dict[str, object] = request.model_dump()
        validate_features(row)
        if not self._slot.acquire(blocking=False):
            raise InferenceBusy
        try:
            scores = self.bundle.predict([row])
            if scores.shape != (1,):
                raise ValueError("Invalid inference shape")
            probability = float(scores[0])
            return ScoreResponse(
                score=probability,
                recommendation="elevated_synthetic_risk"
                if probability >= self.bundle.threshold
                else "low_synthetic_risk",
                model_version=self.bundle.version,
            )
        finally:
            self._slot.release()
