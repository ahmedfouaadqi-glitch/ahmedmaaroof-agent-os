# Playwright Browser E2E

## CI browser path
The Chromium smoke test launches the real Vite frontend and intercepts the backend API with deterministic mock responses. It verifies:
1. Application shell and document title.
2. Entering the API bearer token and automatic connection.
3. Chat navigation and a mocked agent response.
4. Skills workspace and execution of the read-only automation listing tool.
5. Designer cost estimate, explicit approval, mocked generation and image preview.
6. Responsive navigation at a 390px viewport.

The test does not use production API keys, call external providers or incur generation costs.

## CI
- npm run test:e2e runs e2e/smoke.mjs.
- CI installs Playwright temporarily and installs Chromium; Playwright is not a runtime dependency of the web application.
- Successful run: 42846811554.
- Result: Playwright smoke E2E passed; backend and frontend CI jobs also passed.

## Remaining browser tests
- Real microphone permission/recording and audio playback.
- Real OAuth redirect/consent and return path.
- Provider-backed Designer output.
- Automation worker scheduling over time.
- Login/session flows and tenant isolation once those features are implemented.
- Cross-browser testing beyond Chromium.
