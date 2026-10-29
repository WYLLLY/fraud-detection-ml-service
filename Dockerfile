FROM ghcr.io/astral-sh/uv:0.12.23 AS uv
FROM python:3.12.15-slim-trixie AS build
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_PYTHON_DOWNLOADS=never UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.12.15-slim-trixie AS runtime
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    FRAUD_MODEL_DIR=/models OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
RUN apt-get update && apt-get upgrade -y --no-install-recommends && rm -rf /var/lib/apt/lists/*
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --no-create-home app \
    && mkdir /models && chown app:app /models
COPY --from=build /app/.venv /app/.venv
USER 10001:10001
EXPOSE 8002
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8002/health', timeout=2)"
CMD ["uvicorn", "fraud_ml.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8002", "--workers", "1", "--no-access-log", "--no-proxy-headers"]
