# Live Tab Audio Assistant

This repository contains an MVP Chrome extension plus local Python backend for asking an Ollama-powered assistant about the last 25 seconds of audio from the active Chrome tab.

## What it does

1. The Chrome extension starts tab-audio capture only after the user clicks **Start capture**.
2. An offscreen document records one-second `webm/opus` chunks and keeps a rolling 25-second in-memory buffer.
3. The user clicks **Ask about last 25s** or presses `Ctrl+Shift+A`.
4. The extension sends the recent audio and saved context prompt to the local backend over WebSocket.
5. The backend cancels any previous active request for that connection, transcribes with `faster-whisper`, prompts Ollama, and streams tokens back.
6. The popup ignores stale request IDs and updates transcript/answer live.

## Recommended local setup with Docker

Docker is the easiest way to run the backend and Ollama without installing Python dependencies on your host.

### Prerequisites

- Docker Desktop or Docker Engine with the Compose plugin.
- Google Chrome or another Chromium browser that can load unpacked MV3 extensions.
- Enough disk space for the Ollama model and faster-whisper model downloads.

### 1. Start the local services

From the repository root:

```bash
docker compose up --build
```

This starts:

- `backend` on `http://127.0.0.1:8765`
- `ollama` on `http://127.0.0.1:11434`

### 2. Pull the default Ollama model

In a second terminal:

```bash
docker compose exec ollama ollama pull qwen2.5:7b
```

If you set a different `OLLAMA_MODEL`, pull that model instead.

### 3. Verify the backend is reachable

```bash
curl http://127.0.0.1:8765/api/health
```

Expected response:

```json
{"ok": true}
```

### 4. Load the Chrome extension

1. Open `chrome://extensions`.
2. Enable **Developer mode**.
3. Click **Load unpacked**.
4. Select the `extension/` directory from this repository.
5. Open a tab that is playing audio.
6. Open the extension popup and click **Start capture**.
7. Wait at least one second so the rolling buffer has audio.
8. Click **Ask about last 25s** or press `Ctrl+Shift+A`.

### 5. Configure the context prompt

Open the extension options page and set a context prompt, for example:

> The user is watching a programming lecture about React hooks. Answer concisely with practical examples.

The extension stores this prompt in `chrome.storage.local` and sends it with each audio request.

## Optional GPU setup

The default Compose setup is CPU-friendly and uses `WHISPER_DEVICE=cpu` plus `WHISPER_COMPUTE_TYPE=int8` so it can run in more environments.

If you have NVIDIA Container Toolkit installed and want CUDA acceleration for both Ollama and faster-whisper, run:

```bash
docker compose -f compose.yaml -f compose.gpu.yaml up --build
```

You can also copy `.env.example` to `.env` and tune these values:

```bash
cp .env.example .env
```

Common overrides:

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

- If the popup says the backend is disconnected, confirm `docker compose ps` shows the backend running and `curl http://127.0.0.1:8765/api/health` returns `{"ok": true}`.
- If answers fail but transcription works, confirm the Ollama model has been pulled with `docker compose exec ollama ollama list`.
- If captured tab audio becomes silent in your speakers, verify the extension is using the included offscreen capture path, which routes the captured stream back to `AudioContext.destination`.
- If the extension says there is no buffered audio, click **Start capture**, wait a moment, and then trigger **Ask about last 25s**.

## Privacy model

Audio is buffered in memory by the local extension and sent only to `127.0.0.1` after the user explicitly starts capture and triggers an ask action. Transcription and answer generation are designed to run locally through `faster-whisper` and Ollama.
