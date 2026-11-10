from __future__ import annotations

from typing import Any

import httpx


class VoiceServiceError(RuntimeError):
    pass


class VoiceServices:
    """Adapters for OpenAI-compatible Whisper and Kokoro HTTP sidecars."""

    def __init__(self, settings, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self.transport = transport

    async def transcribe(self, audio: bytes, filename: str, content_type: str, language: str | None = None) -> dict[str, Any]:
        base = self.settings.whisper_service_url.rstrip("/")
        if not base:
            raise VoiceServiceError("Whisper service is not configured")
        data = {"model": "whisper-1"}
        if language:
            data["language"] = language
        files = {"file": (filename, audio, content_type or "application/octet-stream")}
        async with httpx.AsyncClient(timeout=90, transport=self.transport) as client:
            response = await client.post(f"{base}/v1/audio/transcriptions", data=data, files=files)
        if response.is_error:
            raise VoiceServiceError(f"Whisper service returned HTTP {response.status_code}")
        try:
            result = response.json()
        except ValueError as exc:
            raise VoiceServiceError("Whisper service returned invalid JSON") from exc
        if not isinstance(result, dict) or not isinstance(result.get("text"), str):
            raise VoiceServiceError("Whisper response must contain a text field")
        return result

    async def speak(self, text: str, voice: str, response_format: str) -> tuple[bytes, str]:
        base = self.settings.kokoro_service_url.rstrip("/")
        if not base:
            raise VoiceServiceError("Kokoro service is not configured")
        payload = {
            "model": "kokoro",
            "input": text,
            "voice": voice,
            "response_format": response_format,
        }
        async with httpx.AsyncClient(timeout=120, transport=self.transport) as client:
            response = await client.post(f"{base}/v1/audio/speech", json=payload)
        if response.is_error:
            raise VoiceServiceError(f"Kokoro service returned HTTP {response.status_code}")
        if not response.content:
            raise VoiceServiceError("Kokoro service returned an empty audio response")
        return response.content, response.headers.get("content-type", "audio/mpeg")

    async def status(self) -> dict[str, dict[str, Any]]:
        return {
            "whisper": await self._probe(self.settings.whisper_service_url),
            "kokoro": await self._probe(self.settings.kokoro_service_url),
        }

    async def _probe(self, base_url: str) -> dict[str, Any]:
        if not base_url:
            return {"configured": False, "reachable": False}
        try:
            async with httpx.AsyncClient(timeout=3, transport=self.transport) as client:
                response = await client.get(f"{base_url.rstrip('/')}/health")
            return {"configured": True, "reachable": response.is_success, "http_status": response.status_code}
        except httpx.HTTPError:
            return {"configured": True, "reachable": False}
