# Live Assistant Backend

Local `aiohttp` WebSocket service that receives recent Chrome tab audio, transcribes it with `faster-whisper`, builds a concise prompt, and streams an Ollama answer back to the extension.

## Docker setup

The repository root includes Docker Compose files for environment-independent local setup.

```bash
# From the repository root
docker compose up --build
```

Pull the default model into the Compose-managed Ollama container:

```bash
docker compose exec ollama ollama pull qwen2.5:7b
```

Health check:

```bash
curl http://127.0.0.1:8765/api/health
```

For NVIDIA GPU acceleration, use the GPU override from the repository root:

```bash
docker compose -f compose.yaml -f compose.gpu.yaml up --build
```

## Manual setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Install and run Ollama separately, then pull a fast local model:

```bash
ollama pull qwen2.5:7b
ollama serve
```

## Run manually

```bash
live-assistant-backend
```

## Environment variables

- `LIVE_ASSISTANT_HOST` default `127.0.0.1` for manual runs and `0.0.0.0` in Docker
- `LIVE_ASSISTANT_PORT` default `8765`
- `WHISPER_MODEL` default `small`
- `WHISPER_DEVICE` default `cuda` for manual runs and `cpu` in Docker Compose
- `WHISPER_COMPUTE_TYPE` default `float16` for manual runs and `int8` in Docker Compose
- `OLLAMA_URL` default `http://127.0.0.1:11434/api/generate` for manual runs and `http://ollama:11434/api/generate` in Docker Compose
- `OLLAMA_MODEL` default `qwen2.5:7b`
- `OLLAMA_TEMPERATURE` default `0.2`
- `OLLAMA_NUM_PREDICT` default `256`
