# Verification record — November 7, 2026

## Passed

- 30 Python tests: URL parsing/IDNA, numeric aliases, malformed IPv6, false-positive regressions, public suffix behavior, no-network analysis, request limits (including chunked bodies), origin checks, assets/headers, AI disabled/success/timeout/malformed-response cases using mocks.
- 17 JavaScript tests: 13 controller tests with simulated camera/image/network behavior; 4 service-worker cache/scope/failure tests.
- 3 actual jsQR decoder checks: two fictional QR images and one blank image.
- JavaScript syntax checks and `git diff --check`.
- In-app Chromium browser: disguised URL, malformed address, Simple/Technical views, AI-disabled fallback. Narrow layout measured 375 CSS pixels with no horizontal overflow. Earlier browser session verified QR image upload.

## Implemented but not fully verified

- Real camera scan on physical desktop/phone hardware, permission dialogs on Safari/Chrome, and installed PWA camera behavior.
- PWA offline/install behavior on physical browsers. Service-worker behavior has unit coverage, not a completed device acceptance test.
- Image-element fallback logic has simulated coverage, not physical Safari coverage.
- Real OpenAI provider compatibility and account/model availability. No live or paid request was made; AI output is constrained composition, not free-form prose.

## Environment observations and remaining work

Windows sandbox blocks the loopback sockets used by Python's event loop. The full backend tests and local preview ran with explicit approved access. No test assertion failed in the expanded suite. Starlette emits a deprecation warning about the httpx-based TestClient; tests pass, and no runtime dependency change was made solely to suppress it.

Physical-phone HTTPS access awaits approval; manual steps are in `DEPLOYMENT.md`. Security heuristics do not verify website contents, reputation, or ownership. Visual warning presentation is unchanged pending human input.
