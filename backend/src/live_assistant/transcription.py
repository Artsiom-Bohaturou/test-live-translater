"""Audio transcription using faster-whisper."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from faster_whisper import WhisperModel

from .config import Settings

_model: WhisperModel | None = None


def _get_model(settings: Settings) -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(
            settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )
    return _model


def _transcribe_sync(path: Path, settings: Settings) -> str:
    model = _get_model(settings)
    segments, _info = model.transcribe(str(path), vad_filter=True)
    return " ".join(segment.text.strip() for segment in segments).strip()


async def transcribe_audio(audio_bytes: bytes, settings: Settings, suffix: str = ".webm") -> str:
    """Persist uploaded audio temporarily and return the transcript."""
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
        handle.write(audio_bytes)
        temp_path = Path(handle.name)
    try:
        return await asyncio.to_thread(_transcribe_sync, temp_path, settings)
    finally:
        temp_path.unlink(missing_ok=True)
