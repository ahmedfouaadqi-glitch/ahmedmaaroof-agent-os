# Designer Engine — Approval-Gated Image Generation

## Implemented
- OpenAI-compatible image generation adapter with a configurable endpoint, model and server-side API key.
- Cost estimation uses the operator-configured per-image estimate; this is an estimate, not a provider invoice.
- Per-request maximum budget enforcement.
- Explicit approval token tied to the exact prompt and image size, expires after 10 minutes and can be used once.
- No provider call is made by the estimate endpoint.
- Provider calls occur only after the authenticated generate endpoint receives a valid approval.
- Base64 PNG/JPEG/WebP output is validated and stored locally; generated artifacts are served through an authenticated endpoint.
- Generation history stores prompt, model, size, estimated cost, MIME type and timestamp.

## API
- `POST /v1/designer/estimate`: creates a short-lived approval and returns the estimated cost.
- `POST /v1/designer/generate`: consumes approval and calls the configured provider.
- `GET /v1/designer/history`: returns recent generated artifacts.
- `GET /v1/designer/artifacts/{id}`: serves the local generated file; requires bearer authentication.

## Configuration
- `IMAGE_PROVIDER_API_KEY`: server-side secret.
- `DESIGNER_PROVIDER_ENDPOINT`: full HTTPS OpenAI-compatible image generation endpoint.
- `DESIGNER_PROVIDER_MODEL`: provider model identifier.
- `DESIGNER_COST_PER_IMAGE_USD`: operator-entered estimated unit cost.
- `DESIGNER_MAX_COST_USD`: explicit maximum estimated cost allowed per request.

All cost settings default to zero, which disables estimates and generation. Do not set a budget until the selected provider's pricing has been verified. No provider credentials were used and no paid generation was triggered during implementation.

## Provider response contract
The configured endpoint must accept an authenticated JSON request with `model`, `prompt`, `size`, `n=1`, and `response_format=b64_json`. It must return `data[0].b64_json` containing a PNG, JPEG or WebP image. Video generation is not implemented in this phase because it requires a distinct provider contract and cost model.

## Limits
- The configured price is an estimate; actual provider billing may differ.
- The budget guard is per generation request, not a monthly spend cap.
- Artifacts are stored on the backend local filesystem; production deployment needs persistent storage, retention and backup policy.
- No real provider, billing, image quality or latency test has been performed.
