# Live Tab Audio Assistant

This repository contains an MVP Chrome extension plus local Python backend for asking an Ollama-powered assistant about the last 25 seconds of audio from the active Chrome tab.

## What it does

1. The Chrome extension starts tab-audio capture only after the user clicks **Start capture**.
2. An offscreen document records one-second `webm/opus` chunks and keeps a rolling 25-second in-memory buffer.
3. The user clicks **Ask about last 25s** or presses `Ctrl+Shift+A`.
4. The extension sends the recent audio and saved context prompt to the local backend over WebSocket.
5. The backend cancels any previous active request for that connection, transcribes with `faster-whisper`, prompts Ollama, and streams tokens back.
6. The popup ignores stale request IDs and updates transcript/answer live.

## Recommended local setup with the desktop GUI

Use the desktop manager if you want to configure models, tokens, GPU/CPU mode, service startup, model downloads, and health checks through a GUI.

### GUI prerequisites

- Python 3.11+ with Tkinter.
- Docker Desktop or Docker Engine with the Compose plugin.
- Google Chrome or another Chromium browser that can load unpacked MV3 extensions.

### Start the GUI

```bash
cd desktop
python -m live_assistant_desktop.app
```

In the GUI:

1. Set the **Ollama model** you want, for example `qwen2.5:7b`.
2. Optional but recommended: set **Hugging Face token** (`HF_TOKEN`) to avoid unauthenticated HF Hub warnings and rate limits when faster-whisper downloads models.
3. Choose CPU mode or enable the NVIDIA GPU Compose override.
4. Click **Save settings**.
5. Click **Start services**.
6. Click **Pull selected Ollama model**.
7. Click **Health check** and confirm the backend returns `{"ok": true}`.
8. Click **Open Chrome extension folder**, then load that folder from `chrome://extensions`.

The GUI saves settings into `.env`, starts/stops Docker Compose, pulls Ollama models, lists installed models, and copies the extension folder path.

## Recommended local setup with Docker CLI

Docker is the easiest terminal-based way to run the backend and Ollama without installing Python backend dependencies on your host.

### Prerequisites

- Docker Desktop or Docker Engine with the Compose plugin.
- Google Chrome or another Chromium browser that can load unpacked MV3 extensions.
- Enough disk space for the Ollama model and faster-whisper model downloads.

### 1. Configure environment values

Copy the sample environment file:

```bash
cp .env.example .env
```

If you have a Hugging Face token, set it in `.env`:

```env
HF_TOKEN=hf_your_token_here
```

This fixes the faster-whisper/Hugging Face warning about unauthenticated HF Hub requests and gives you better download rate limits.

### 2. Start the local services

From the repository root:

```bash
docker compose up --build
```

This starts:

- `backend` on `http://127.0.0.1:8765`
- `ollama` on `http://127.0.0.1:11434`

### 3. Pull the selected Ollama model with retry

In a second terminal, use the Compose pull helper instead of `docker compose exec ollama ollama pull ...`:

```bash
docker compose --profile tools run --rm ollama-pull
```

The helper waits for Ollama to become healthy and retries transient registry/network failures such as `Error: EOF`. If you set a different `OLLAMA_MODEL`, it pulls that model from `.env`.

### 4. Verify the backend is reachable

```bash
curl http://127.0.0.1:8765/api/health
```

Expected response:

```json
{"ok": true}
```

### 5. Load the Chrome extension

1. Open `chrome://extensions`.
2. Enable **Developer mode**.
3. Click **Load unpacked**.
4. Select the `extension/` directory from this repository.
5. Open a tab that is playing audio.
6. Open the extension popup and click **Start capture**.
7. Wait at least one second so the rolling buffer has audio.
8. Click **Ask about last 25s** or press `Ctrl+Shift+A`.

### 6. Configure the context prompt

Open the extension options page and set a context prompt, for example:

> The user is watching a programming lecture about React hooks. Answer concisely with practical examples.

The extension stores this prompt in `chrome.storage.local` and sends it with each audio request.

## Optional GPU setup

The default Compose setup is CPU-friendly and uses `WHISPER_DEVICE=cpu` plus `WHISPER_COMPUTE_TYPE=int8` so it can run in more environments.

If you have NVIDIA Container Toolkit installed and want CUDA acceleration for both Ollama and faster-whisper, run:

```bash
docker compose -f compose.yaml -f compose.gpu.yaml up --build
```

Common `.env` overrides:

- `HF_TOKEN=hf_...` to authenticate faster-whisper model downloads from Hugging Face.
- `WHISPER_MODEL=small` for faster transcription or `medium` for better accuracy.
- `OLLAMA_MODEL=qwen2.5:7b`, `mistral:7b`, or another locally pulled model.
- `OLLAMA_NUM_PREDICT=256` to keep responses concise.

## Manual backend setup without Docker

Use this if you prefer to run Python and Ollama directly on the host:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .
export HF_TOKEN=hf_your_token_here  # optional but recommended
ollama pull qwen2.5:7b
live-assistant-backend
```

If you do not have CUDA, override the Whisper settings before starting:

```bash
WHISPER_DEVICE=cpu WHISPER_COMPUTE_TYPE=int8 live-assistant-backend
```

## Configuration

The extension defaults to `ws://127.0.0.1:8765/ws`. Backend defaults are documented in `backend/README.md`.

## Troubleshooting

- If you see `Warning: You are sending unauthenticated requests to the HF Hub`, set `HF_TOKEN` in `.env` or through the desktop GUI, then restart services.
- If the popup says the backend is disconnected, confirm `docker compose ps` shows the backend running and `curl http://127.0.0.1:8765/api/health` returns `{"ok": true}`.
- If answers fail but transcription works, confirm the Ollama model has been pulled with `docker compose exec ollama ollama list`.
- If `docker compose exec ollama ollama pull qwen2.5:7b` fails with `Error: EOF`, run `docker compose --profile tools run --rm ollama-pull`; this uses the same Compose network, waits for the Ollama healthcheck, and retries the pull.
- If captured tab audio becomes silent in your speakers, verify the extension is using the included offscreen capture path, which routes the captured stream back to `AudioContext.destination`.
- If the extension says there is no buffered audio, click **Start capture**, wait a moment, and then trigger **Ask about last 25s**.

## Privacy model

Audio is buffered in memory by the local extension and sent only to `127.0.0.1` after the user explicitly starts capture and triggers an ask action. Transcription and answer generation are designed to run locally through `faster-whisper` and Ollama.
