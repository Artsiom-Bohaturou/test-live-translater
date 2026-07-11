"""Prompt construction helpers."""

BASE_INSTRUCTION = (
    "You are a low-latency assistant helping the user understand audio from "
    "a Chrome tab. Answer directly and concisely. If the transcript is unclear, "
    "say what you heard and provide the most likely useful answer."
)


def build_prompt(transcript: str, context_prompt: str = "") -> str:
    """Build the final prompt sent to Ollama."""
    context = context_prompt.strip() or "No extra context was provided."
    heard = transcript.strip() or "[No speech was confidently transcribed.]"
    return (
        f"{BASE_INSTRUCTION}\n\n"
        f"User context:\n{context}\n\n"
        f"Transcript:\n{heard}\n\n"
        "Answer:"
    )
