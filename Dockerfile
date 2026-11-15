FROM ghcr.io/astral-sh/uv:0.12.23@sha256:61d393e44e249f2e4b526b6c7ddcecce245946826e608e11c93ad4f5bba55b21 AS uv
FROM ubuntu:24.04@sha256:2198e4c65076e9cb0b3d695219df667c0e3b0072da64ca3c2648aca17dcecaf5 AS base
RUN apt-get update && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends ca-certificates python3.12 libstdc++6 libgomp1 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app

FROM base AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_PYTHON_DOWNLOADS=never UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
RUN uv sync --python /usr/bin/python3.12 --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --python /usr/bin/python3.12 --frozen --no-dev --no-editable

FROM base AS runtime
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    FRAUD_MODEL_DIR=/models OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --no-create-home app \
    && mkdir /models && chown app:app /models
COPY --from=build /app/.venv /app/.venv
RUN rm -f /usr/bin/mount /usr/bin/umount /usr/bin/nsenter /usr/bin/infocmp \
    && find / -xdev -type f -perm /6000 -exec chmod a-s {} +
USER 10001:10001
EXPOSE 8002
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8002/health', timeout=2)"
CMD ["uvicorn", "fraud_ml.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8002", "--workers", "1", "--no-access-log", "--no-proxy-headers"]
