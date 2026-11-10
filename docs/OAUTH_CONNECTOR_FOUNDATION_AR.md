# Email and Calendar OAuth Foundation

## Implemented
- Provider-neutral OAuth 2.0 authorization-code flow with PKCE (S256).
- Random, one-time state values stored as SHA-256 hashes with a 10-minute expiry.
- PKCE verifier encrypted at rest while authorization is pending.
- OAuth token exchange through HTTPS-configured provider endpoints.
- Access/refresh token response encrypted at rest using Fernet before SQLite persistence.
- Status endpoint returns only authorization metadata and never returns token values.
- Disconnect deletes the stored token record.
- Separate configuration for email and calendar clients so each can use a provider and scopes appropriate to the deployment.

## API
- `POST /v1/oauth/email/start` and `POST /v1/oauth/calendar/start`: authenticated; returns an authorization URL.
- `GET /v1/oauth/{integration}/callback`: public callback; requires a valid one-time state and code.
- `GET /v1/oauth/{integration}/status`: authenticated; reports whether an authorization record exists.
- `DELETE /v1/oauth/{integration}`: authenticated; deletes the stored authorization record.

The callback is intentionally public because the identity provider redirects the user's browser to it. CSRF protection is provided by a random, expiring, single-use state value and PKCE.

## Required server-side configuration
For each integration, configure authorization URL, token URL, client ID, client secret, redirect URI and least-privilege scopes. Both provider endpoints must use HTTPS.

Generate a Fernet encryption key in a trusted environment:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
Store the result as `OAUTH_TOKEN_ENCRYPTION_KEY` in the backend secret manager only. Losing or rotating this key without re-encrypting stored tokens makes existing tokens unreadable.

## Deliberate limits
- The identity provider is not selected in code. Configure Google, Microsoft or another OAuth 2.0 provider using its official endpoints and registered redirect URI.
- This foundation does not yet implement provider-specific Gmail/Outlook message listing, reading, sending, or Google/Microsoft calendar operations.
- Automatic refresh-token renewal is implemented when an access token is within 60 seconds of expiry. Provider-side token revocation is not yet implemented; disconnect removes the local encrypted record.
- The existing API still uses one shared backend bearer key; this is a single-owner connector foundation, not multi-user account isolation.
- No OAuth secrets or real provider credentials were supplied or used. No consent flow was run against a real identity provider.

## Next implementation step
After selecting the email/calendar provider, add its API adapter with read-only operations first, provider-side token revocation, and integration tests against a controlled test tenant. Sending mail and creating calendar events require explicit write scopes and separate approval controls.
