# Live Assistant Backend

Local `aiohttp` WebSocket service that receives recent Chrome tab audio, transcribes it with `faster-whisper`, builds a concise prompt, and streams an Ollama answer back to the extension.

## Desktop GUI setup

The repository includes a Tkinter desktop manager for configuring `.env`, starting/stopping Docker Compose, pulling Ollama models, listing models, and running health checks.

```bash
cd desktop
python -m live_assistant_desktop.app
```

Set `HF_TOKEN` in the GUI if you want authenticated faster-whisper downloads from Hugging Face. This prevents the warning about unauthenticated HF Hub requests and improves rate limits.

## Docker setup

The repository root includes Docker Compose files for environment-independent local setup.

```bash
# From the repository root
cp .env.example .env
# Optional but recommended: edit .env and set HF_TOKEN=hf_your_token_here
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
- `HF_TOKEN` optional Hugging Face token used by faster-whisper/Hugging Face downloads to avoid unauthenticated rate-limit warnings
- `OLLAMA_URL` default `http://127.0.0.1:11434/api/generate` for manual runs and `http://ollama:11434/api/generate` in Docker Compose
- `OLLAMA_MODEL` default `qwen2.5:7b`
- `OLLAMA_TEMPERATURE` default `0.2`
- `OLLAMA_NUM_PREDICT` default `256`
