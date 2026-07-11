"""Streaming Ollama client."""

from __future__ import annotations

from collections.abc import AsyncIterator
import json

from aiohttp import ClientSession

from .config import Settings


async def stream_completion(prompt: str, settings: Settings) -> AsyncIterator[str]:
    """Yield response tokens from Ollama's streaming generate endpoint."""
    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": True,
        "options": {
            "temperature": settings.ollama_temperature,
            "num_predict": settings.ollama_num_predict,
        },
    }
    async with ClientSession() as session:
        async with session.post(settings.ollama_url, json=payload) as response:
            response.raise_for_status()
            async for raw_line in response.content:
                line = raw_line.strip()
                if not line:
                    continue
                data = json.loads(line)
                token = data.get("response", "")
                if token:
                    yield token
                if data.get("done"):
                    break
