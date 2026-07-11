"""Per-WebSocket session orchestration and cancellation."""

from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass
from typing import Any

from aiohttp import web

from .config import Settings
from .ollama_client import stream_completion
from .prompts import build_prompt
from .transcription import transcribe_audio


@dataclass(slots=True)
class AudioRequest:
    request_id: str
    audio_format: str
    context_prompt: str
    audio_base64: str


class ClientSession:
    """Owns at most one active transcription/generation task per client."""

    def __init__(self, websocket: web.WebSocketResponse, settings: Settings) -> None:
        self.websocket = websocket
        self.settings = settings
        self.active_task: asyncio.Task[None] | None = None
        self.active_request_id: str | None = None

    async def close(self) -> None:
        await self.cancel_active()

    async def cancel_active(self) -> None:
        if self.active_task and not self.active_task.done():
            self.active_task.cancel()
            try:
                await self.active_task
            except asyncio.CancelledError:
                pass
        self.active_task = None
        self.active_request_id = None

    async def handle_message(self, message: dict[str, Any]) -> None:
        message_type = message.get("type")
        if message_type == "cancel":
            await self.cancel_active()
            await self._send({"type": "cancelled", "requestId": message.get("requestId")})
            return
        if message_type != "ask_audio":
            await self._send({"type": "error", "message": f"Unsupported message type: {message_type}"})
            return
        request = AudioRequest(
            request_id=str(message.get("requestId", "")),
            audio_format=str(message.get("audioFormat", "webm-opus")),
            context_prompt=str(message.get("contextPrompt", "")),
            audio_base64=str(message.get("audioBase64", "")),
        )
        if not request.request_id or not request.audio_base64:
            await self._send({"type": "error", "requestId": request.request_id, "message": "Missing requestId or audioBase64"})
            return
        await self.start_request(request)

    async def start_request(self, request: AudioRequest) -> None:
        await self.cancel_active()
        self.active_request_id = request.request_id
        self.active_task = asyncio.create_task(self._run_request(request))

    async def _run_request(self, request: AudioRequest) -> None:
        try:
            await self._send({"type": "status", "requestId": request.request_id, "message": "Transcribing audio..."})
            audio_bytes = base64.b64decode(request.audio_base64)
            transcript = await transcribe_audio(audio_bytes, self.settings)
            await self._send({"type": "transcript", "requestId": request.request_id, "text": transcript})
            prompt = build_prompt(transcript, request.context_prompt)
            await self._send({"type": "status", "requestId": request.request_id, "message": "Generating answer..."})
            async for token in stream_completion(prompt, self.settings):
                if request.request_id != self.active_request_id:
                    return
                await self._send({"type": "token", "requestId": request.request_id, "text": token})
            await self._send({"type": "done", "requestId": request.request_id})
        except asyncio.CancelledError:
            await self._send({"type": "cancelled", "requestId": request.request_id})
            raise
        except Exception as exc:  # noqa: BLE001 - errors are surfaced to the local UI.
            await self._send({"type": "error", "requestId": request.request_id, "message": str(exc)})

    async def _send(self, payload: dict[str, Any]) -> None:
        if not self.websocket.closed:
            await self.websocket.send_json(payload)
