# Live Assistant Desktop Manager

This is a small Tkinter GUI for users who prefer not to operate Docker Compose from the terminal.

## Requirements

- Python 3.11+
- Tkinter support for your Python installation
- Docker Desktop or Docker Engine with the Compose plugin

## Run from source

```bash
cd desktop
python -m live_assistant_desktop.app
```

Or install it in a virtual environment:

```bash
cd desktop
python -m venv .venv
source .venv/bin/activate
pip install -e .
live-assistant-desktop
```

## What the GUI can configure

- Ollama model name, such as `qwen2.5:7b`, `mistral:7b`, or `llama3.1:8b`
- Whisper model, device, and compute type
- Ollama temperature and response token limit
- Hugging Face token (`HF_TOKEN`) to avoid unauthenticated model-download warnings and rate limits
- CPU or NVIDIA GPU Compose mode

## What the GUI can do

- Save settings into the repository `.env` file
- Start or stop the Docker Compose services
- Pull the selected Ollama model with the Compose retry helper, which is safer than direct `docker compose exec ollama ollama pull ...` after transient `Error: EOF` failures
- List installed Ollama models
- Run the backend health check
- Copy the Chrome extension folder path for `chrome://extensions` → **Load unpacked**
