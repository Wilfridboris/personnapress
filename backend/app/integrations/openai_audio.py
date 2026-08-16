"""OpenAI Whisper audio transcription integration.

All OpenAI audio API calls originate exclusively from this module.
Audio bytes are passed in-memory and never written to disk or storage.
"""

import httpx

from app.core.config import settings

_OPENAI_TRANSCRIPTION_URL = "https://api.openai.com/v1/audio/transcriptions"
_MODEL = "gpt-4o-mini-transcribe"


async def transcribe(content: bytes, mime_type: str) -> str:
    """Transcribe audio bytes via OpenAI Whisper and return the transcript string.

    Raises an exception on non-2xx response or network error.
    """
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            _OPENAI_TRANSCRIPTION_URL,
            headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
            data={"model": _MODEL},
            files={"file": ("audio", content, mime_type)},
        )
    response.raise_for_status()
    text = response.json().get("text")
    if text is None:
        raise ValueError("OpenAI transcription response did not include a 'text' field.")
    return text
