FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    LIVE_ASSISTANT_HOST=0.0.0.0 \
    LIVE_ASSISTANT_PORT=8765 \
    WHISPER_DEVICE=cpu \
    WHISPER_COMPUTE_TYPE=int8

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --upgrade pip \
    && pip install .

EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:${LIVE_ASSISTANT_PORT}/api/health || exit 1

CMD ["live-assistant-backend"]
