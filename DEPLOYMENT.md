# HTTPS and real-phone testing: preparation only

Nothing has been deployed, exposed to a network, or connected to a new service. AI remains disabled. Choose and approve an access method before executing deployment steps.

## Practical options

1. **A user-owned HTTPS test host (recommended if already available).** Run this FastAPI app behind the host's HTTPS proxy. One origin serves both the interface and `/api/*`, avoiding cross-origin setup. Review provider costs and public access before authorizing.
2. **An approved temporary HTTPS tunnel.** Fastest when no hosting account exists, but sends traffic through a third party and may expose the app to anyone with its address. Requires your explicit approval and any required installation; no tunnel is currently configured.
3. **Local trusted HTTPS.** Keeps traffic within your environment but needs a certificate trusted by the phone, network binding, and possibly firewall changes. More setup for this deadline. Never disable browser security or bypass certificate warnings.

## Host configuration to review before publication

- Python 3.12+, install `requirements.txt` in an isolated environment. Serve `main:app` using Uvicorn; no frontend build.
- Preserve the whole `static/` directory and its locally vendored QR decoder.
- Keep frontend and API on the same HTTPS origin. Forward the original Host and scheme correctly. Only trust forwarded headers from the known reverse proxy, never arbitrary clients.
- Health check: `GET /health` returns `status: ok`. Ensure the proxy leaves `/sw.js` at the root with a JavaScript content type and revalidation enabled.
- Set `PLUQ_AI_ENABLED=false`; do not add a key until API use and costs are approved. No secrets belong in `static/` or Git.
- Apply a request body limit and connection timeout at the proxy. Application-level POST bodies are also capped at 16 KiB, including chunked uploads.
- Add a per-client request rate limit and trusted host restrictions at the proxy before public access, especially before enabling AI. These deployment controls have not been provisioned.
- Disable request-body logging; URLs may contain sensitive tokens. Use only fictional QR fixtures in the first phone tests.
- Run every applicable check in `MANUAL_TESTS.md` on HTTPS and installed mode. Verify no requests to scanned destinations.

Do not expose the laptop with `--host 0.0.0.0`, alter firewall rules, sign up for hosting, or activate a tunnel until approved. The checked-in launcher intentionally binds only to `127.0.0.1`.
