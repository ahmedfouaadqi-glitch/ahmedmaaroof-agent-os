# Voice Service Contracts

## Scope
The backend now exposes authenticated API adapters for OpenAI-compatible Whisper STT and Kokoro TTS sidecars. The adapters do not install, launch or provision either model service.

## Required service contracts
- Whisper base URL: `WHISPER_SERVICE_URL`; endpoint: `POST /v1/audio/transcriptions`; multipart fields: `file`, `model=whisper-1`, optional `language`; JSON response must contain a string `text`.
- Kokoro base URL: `KOKORO_SERVICE_URL`; endpoint: `POST /v1/audio/speech`; JSON fields: `model=kokoro`, `input`, `voice`, `response_format`; response body is audio bytes.
- Both services should expose `GET /health` for readiness probing.

These are explicit adapter contracts. A local deployment with different route names or payload formats needs a matching adapter; no compatibility with an untested sidecar is assumed.

## API
- `GET /v1/voice/status` probes both sidecars.
- `POST /v1/voice/transcribe` accepts multipart audio up to 15 MB.
- `POST /v1/voice/speak` accepts validated JSON and returns audio bytes.
- All endpoints require the backend bearer API key.

## Limits and verification
- Provider calls use bounded HTTP timeouts.
- No credentials are currently required for the documented local sidecar contract; do not expose these services publicly without authentication and network controls.
- Unit tests use HTTPX MockTransport. They verify request/response contracts, not the availability or performance of the user's local Whisper/Kokoro installations.
- Frontend microphone capture/playback and live-device testing remain outstanding.
