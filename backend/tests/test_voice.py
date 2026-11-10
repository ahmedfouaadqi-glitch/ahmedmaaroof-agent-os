import asyncio
from types import SimpleNamespace

import httpx
import pytest

from app.services.voice import VoiceServiceError, VoiceServices


def test_whisper_transcription_uses_openai_compatible_contract():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["content_type"] = request.headers["content-type"]
        return httpx.Response(200, json={"text": "مرحبا"})

    service = VoiceServices(
        SimpleNamespace(whisper_service_url="http://whisper.local", kokoro_service_url=""),
        transport=httpx.MockTransport(handler),
    )
    result = asyncio.run(service.transcribe(b"audio-bytes", "sample.wav", "audio/wav", "ar"))
    assert result["text"] == "مرحبا"
    assert seen["url"] == "http://whisper.local/v1/audio/transcriptions"
    assert "multipart/form-data" in seen["content_type"]


def test_kokoro_speech_returns_audio_bytes_and_content_type():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["payload"] = request.read().decode()
        return httpx.Response(200, content=b"fake-audio", headers={"content-type": "audio/mpeg"})

    service = VoiceServices(
        SimpleNamespace(whisper_service_url="", kokoro_service_url="http://kokoro.local"),
        transport=httpx.MockTransport(handler),
    )
    audio, media_type = asyncio.run(service.speak("Hello", "af_heart", "mp3"))
    assert audio == b"fake-audio"
    assert media_type == "audio/mpeg"
    assert seen["url"] == "http://kokoro.local/v1/audio/speech"
    assert '"input":"Hello"' in seen["payload"]


def test_unconfigured_voice_provider_fails_closed():
    service = VoiceServices(
        SimpleNamespace(whisper_service_url="", kokoro_service_url="")
    )
    with pytest.raises(VoiceServiceError, match="not configured"):
        asyncio.run(service.transcribe(b"audio", "sample.wav", "audio/wav"))
