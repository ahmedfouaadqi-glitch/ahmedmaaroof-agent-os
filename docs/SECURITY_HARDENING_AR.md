# Security Hardening — Initial Controls

## Implemented
- SQLite-backed fixed-window rate limiter for authenticated API requests.
- Rate-limit buckets are keyed by a SHA-256 hash of client IP plus bearer credential; raw credentials are not persisted in the limiter table.
- Separate IP-based limit for the public OAuth callback.
- Configurable authenticated/public request limits and window duration.
- Configurable request body limit using the Content-Length header.
- Response headers: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, and `X-Permitted-Cross-Domain-Policies`.
- HSTS is added only when the ASGI request scheme is HTTPS.

## Configuration
- `RATE_LIMIT_PER_MINUTE=120`
- `PUBLIC_RATE_LIMIT_PER_MINUTE=30`
- `RATE_LIMIT_WINDOW_SECONDS=60`
- `MAX_BODY_BYTES=20971520`

These are defaults, not production capacity guarantees. Tune them after observing normal usage and provider latency.

## Remaining security requirements
- Authentication is still a single shared bearer API key. No account registration, password login, JWT/session lifecycle or per-user role model exists.
- No workspace/tenant isolation is implemented. Do not expose this backend to multiple untrusted users.
- The limiter is fixed-window and SQLite-backed; it is not a distributed token bucket or a substitute for edge/WAF controls.
- The body-size middleware uses Content-Length; deployments must also enforce request limits at the reverse proxy/load balancer to cover chunked requests.
- Trust proxy headers only from known reverse proxies; the application currently keys by the ASGI client address.
- Secrets remain environment/secret-manager configuration. Production deployment must add rotation, least-privilege access, backups and incident response.
- A formal security review, dependency scanning, CSRF review for browser session auth, and penetration testing remain outstanding.

## Operational boundary
This phase adds baseline abuse controls without pretending to solve identity or data isolation. Shared bearer authentication remains the security boundary until tenant-scoped storage and user/session authorization are implemented end-to-end.
