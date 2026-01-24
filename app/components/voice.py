import asyncio
import os
import tempfile
import threading
from typing import Any, Dict, Optional, Tuple

import edge_tts
from faster_whisper import WhisperModel

from app.common.logger import get_logger
from app.config.config import (
    EDGE_TTS_OUTPUT_FORMAT,
    EDGE_TTS_PITCH,
    EDGE_TTS_RATE,
    EDGE_TTS_VOICE,
    WHISPER_COMPUTE_TYPE,
    WHISPER_DEVICE,
    WHISPER_LANGUAGE,
    WHISPER_MODEL_SIZE,
)

logger = get_logger(__name__)

# -----------------------------
# Whisper (STT) - singleton
# -----------------------------
_WHISPER_MODEL: Optional[WhisperModel] = None
_WHISPER_LOCK = threading.Lock()


def _get_whisper_model() -> WhisperModel:
    """Singleton Whisper model loader (thread-safe)."""
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        with _WHISPER_LOCK:
            if _WHISPER_MODEL is None:
                logger.info(
                    "Loading Whisper model size=%s device=%s compute_type=%s",
                    WHISPER_MODEL_SIZE,
                    WHISPER_DEVICE,
                    WHISPER_COMPUTE_TYPE,
                )
                _WHISPER_MODEL = WhisperModel(
                    WHISPER_MODEL_SIZE,
                    device=WHISPER_DEVICE,
                    compute_type=WHISPER_COMPUTE_TYPE,
                )
    return _WHISPER_MODEL


def transcribe_audio(file_storage) -> Tuple[str, Dict[str, Any]]:
    """Transcribe an uploaded audio file (Werkzeug FileStorage) -> (transcript, meta)."""
    if file_storage is None:
        raise ValueError("Audio file is required.")

    suffix = os.path.splitext(getattr(file_storage, "filename", "") or "")[1] or ".wav"
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            file_storage.save(temp_file.name)
            temp_path = temp_file.name

        model = _get_whisper_model()

        language = (WHISPER_LANGUAGE or "").strip() or None
        segments, info = model.transcribe(temp_path, language=language, task="transcribe")

        parts = []
        for segment in segments:
            text = getattr(segment, "text", "")
            if text:
                parts.append(text.strip())

        transcript = " ".join(parts).strip()
        meta = {
            "language": getattr(info, "language", None),
            "duration": getattr(info, "duration", None),
        }
        return transcript, meta

    finally:
        if temp_path:
            try:
                os.remove(temp_path)
            except OSError:
                logger.warning("Failed to remove temp audio file: %s", temp_path)


# -----------------------------
# Edge TTS (TTS)
# -----------------------------
async def _synthesize(
    text: str,
    voice: str,
    rate: str,
    pitch: str,
    output_format: str,
) -> bytes:
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,
        pitch=pitch,
        output_format=output_format,
    )

    buf = bytearray()
    async for chunk in communicate.stream():
        if chunk.get("type") == "audio":
            buf.extend(chunk.get("data", b""))
    return bytes(buf)


async def synthesize_speech_async(
    text: str,
    voice: str = EDGE_TTS_VOICE,
    rate: str = EDGE_TTS_RATE,
    pitch: str = EDGE_TTS_PITCH,
    output_format: str = EDGE_TTS_OUTPUT_FORMAT,
) -> bytes:
    """Async TTS: safe to call inside async runtime."""
    if not text or not text.strip():
        raise ValueError("Text is required for TTS.")
    return await _synthesize(text.strip(), voice, rate, pitch, output_format)


def _run_coro_safely(coro) -> Any:
    """
    Run coroutine from sync code:
    - If NO event loop is running in this thread -> asyncio.run(coro)
    - If an event loop IS running -> run coroutine in a dedicated thread (new loop)
    """
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            result_holder: Dict[str, Any] = {}
            err_holder: Dict[str, BaseException] = {}

            def _worker():
                try:
                    result_holder["result"] = asyncio.run(coro)
                except BaseException as e:
                    err_holder["err"] = e

            t = threading.Thread(target=_worker, daemon=True)
            t.start()
            t.join()

            if "err" in err_holder:
                raise err_holder["err"]
            return result_holder.get("result")

    except RuntimeError:
        # No running loop in this thread
        return asyncio.run(coro)

    return asyncio.run(coro)


def synthesize_speech(
    text: str,
    voice: str = EDGE_TTS_VOICE,
    rate: str = EDGE_TTS_RATE,
    pitch: str = EDGE_TTS_PITCH,
    output_format: str = EDGE_TTS_OUTPUT_FORMAT,
) -> bytes:
    """Sync TTS: use from normal Flask routes."""
    if not text or not text.strip():
        raise ValueError("Text is required for TTS.")
    return _run_coro_safely(_synthesize(text.strip(), voice, rate, pitch, output_format))


def tts_mime_type(output_format: str) -> str:
    output_format = (output_format or "").lower()
    if "mp3" in output_format:
        return "audio/mpeg"
    if "ogg" in output_format:
        return "audio/ogg"
    if "webm" in output_format:
        return "audio/webm"
    if "wav" in output_format or "pcm" in output_format:
        return "audio/wav"
    return "application/octet-stream"


# Optional: list voices for UI dropdown
async def list_voices_async() -> list:
    return await edge_tts.list_voices()


def list_voices() -> list:
    return _run_coro_safely(list_voices_async())