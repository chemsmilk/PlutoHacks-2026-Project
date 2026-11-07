# PluQ

Mobile-first QR URL risk scanner for PlutoHacks 2026. Scan a camera or image, or paste a URL. Understand warning signs without visiting the destination.

## Run locally on this computer

Open PowerShell in this project folder:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 in your browser. Keep the terminal open; Ctrl+C stops the server. Alternatively run `./start.ps1`. Dependencies are already installed in the project-local `.venv`; no system-wide installation or API key is needed.

For another computer with Python 3.12 or later, create a virtual environment with `python -m venv .venv`, then install `requirements-dev.txt` with that environment's Python and pip. On macOS/Linux the executable is `.venv/bin/python`. No npm or frontend build is needed. jsQR 1.4.0 and its license are vendored in `static/vendor`.

## Two-minute demo

1. Select **Ordinary URL**. No obvious indicators does not mean safe.
2. Select **Disguised URL**. The actual destination is `account-check.test`, not the name before `@`.
3. Toggle **Simple explanation** and **Technical details**. Every finding explains what was detected, why it matters, and what to do.
4. Open **QR demo cards** on another screen and scan with a camera, or upload `static/demo-disguised.png`.
5. Select **Personalize explanation with AI**. With AI disabled, the app honestly reports rule-based fallback.
6. Optionally download a JSON report. It contains the raw scanned content; share intentionally.

Demo codes use fictional `.test` destinations. No live malicious destinations or paid AI requests are used in tests.

## Phone camera and installation

Camera access requires localhost on the computer running the app, or trusted HTTPS. A phone's localhost points to the phone, not your laptop. **Phone-accessible HTTPS is not configured yet.** Ask before setting up hosting, a tunnel, firewall changes, or certificates. Do not bypass browser certificate warnings. For now use the laptop camera or image upload for the demo.

The PWA includes a manifest, icons, and service worker. Supported browsers offer Install app; iOS generally uses Safari Share → Add to Home Screen. Physical-phone camera and installation testing remain necessary. The cached shell and decoder can work offline after an online visit; URL analysis needs the running backend. Offline failure is explained in the UI.

Images remain on the device. Decoded text goes to the local backend. There is no scan database, saved history, or response cache; Clear scan removes the current page result.

## Detection and limits

FastAPI performs URL parsing and lexical checks. It does not make DNS, HTTP, preview, favicon, certificate, redirect, or threat-list requests to scanned destinations. tldextract uses its packaged public suffix snapshot, with network refresh disabled. Decoded content is rendered as text, not links. The browser has a restrictive same-origin Content Security Policy.

Checks include HTTP, text before `@`, numeric/private hosts, internationalized names, selected brand tokens outside expected domains, known shorteners, unusual ports, encoded delimiters/nested URLs, and deep subdomains. These are indicators, not proof of phishing. Brand matching covers a small explicit list, not all lookalikes. Unknown suffixes display the full hostname rather than guessing a registrable domain. Technical details state the domain basis. Non-web QR content and ambiguous addresses are not executed. No live reputation integration is included.

This is a local hackathon MVP. Before public deployment add proxy body-size limits, rate limiting, trusted-host configuration, and AI budget controls.

## Optional real AI integration

The OpenAI Responses API integration is implemented but **disabled by default**. Tests mock responses and use no real credentials. A key alone does not enable requests. Activation requires `PLUQ_AI_ENABLED=true`, `OPENAI_API_KEY`, and `OPENAI_MODEL` in the server's environment; restart after changing them. Use a structured-output-capable model available to your account. `.env.example` documents settings but is not automatically loaded.

Do not activate paid API use until costs are approved. Never put keys in browser code or Git. The server calls only the fixed OpenAI endpoint after an explanation request, with no tools, browsing, or redirects. Timeouts and invalid output fall back to rules.

To enforce the no-invented-findings requirement, AI generates a constrained explanation plan: it prioritizes observed findings and selects a verified introduction. The UI composes what/why/action clauses from verified evidence. This is real model-driven composition when enabled, **not unrestricted generated prose**. AI cannot change the verdict, omit findings, add claims, or call a URL safe. Unknown/missing IDs and invalid output are rejected. Only generic indicator descriptions are sent; the raw URL, hostname, path, query, credentials, and QR image are withheld. Technical evidence stays deterministic.

Free-form AI wording would need an explicitly accepted reliability tradeoff: schema validation alone cannot prove prose is factually grounded. Official reference: https://developers.openai.com/api/docs/guides/structured-outputs

## Tests

```powershell
.\.venv\Scripts\python.exe scripts/generate_demo.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node tests/qr-test.cjs
node --test tests/frontend.test.cjs tests/service-worker.test.cjs
node --check static/app.js
node --check static/sw.js
```

The backend suite covers parsing, disguised hosts, local IPs, non-web payloads, IDNA, suffix extraction, network-free analysis, API input/origin checks, headers/assets, and mocked AI success, timeout, and hallucination rejection. QR checks decode the actual fictional image fixtures with the vendored decoder and reject a blank image.

## Original project

For human review and acceptance: see [MANUAL_TESTS.md](MANUAL_TESTS.md), [REVIEW.md](REVIEW.md), [TEST_RESULTS.md](TEST_RESULTS.md), and [DEPLOYMENT.md](DEPLOYMENT.md). These distinguish automated checks from still-pending physical-device and live-AI verification.

Git was clean before changes. The original prototype remains in commit `2e28264` (Merge GitHub README). `git show 2e28264:app.py` displays it without changing files. Streamlit simulations and the C++ benchmark/bridge were retired; FastAPI was retained. No push or public deployment was performed.
