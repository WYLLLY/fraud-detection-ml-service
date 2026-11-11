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
# Trixie has no fixed package for the SQLite 3.54 advisories. Install only the
# verified Debian library; util-linux requires SQLite through liblastlog2.
RUN set -eu; \
    case "$(dpkg --print-architecture)" in \
      amd64) archive=a20ce6080f324fec313559502446a666b67599f4; sha256=7789bf0b2338b781de388d83d7c473f9386c9ef638af110b5c1b3d1debb36f00 ;; \
      arm64) archive=bca4131353b1679d8d1b06c78061fbd127669e12; sha256=27416ae5fd9a8a491cacc2316cb08ebf31ac0d3d628da5576e04eeba365605a4 ;; \
      *) echo 'The pinned SQLite runtime is available for amd64 and arm64' >&2; exit 1 ;; \
    esac; \
    python -c 'import pathlib, sys, urllib.request; pathlib.Path("/tmp/sqlite.deb").write_bytes(urllib.request.urlopen(sys.argv[1], timeout=30).read())' \
      "https://snapshot.debian.org/file/${archive}"; \
    echo "${sha256}  /tmp/sqlite.deb" | sha256sum --check; \
    apt-get install -y --no-install-recommends /tmp/sqlite.deb; \
    rm /tmp/sqlite.deb
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --no-create-home app \
    && mkdir /models && chown app:app /models
COPY --from=build /app/.venv /app/.venv
# These privileged/terminal helpers are not used by numeric inference.
RUN rm -f /usr/bin/mount /usr/bin/umount /usr/bin/nsenter /usr/bin/infocmp \
    && find / -xdev -type f -perm /6000 -exec chmod a-s {} +
USER 10001:10001
EXPOSE 8002
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8002/health', timeout=2)"
CMD ["uvicorn", "fraud_ml.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8002", "--workers", "1", "--no-access-log", "--no-proxy-headers"]
