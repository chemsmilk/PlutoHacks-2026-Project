# PluQ: your hands-on acceptance checks

Run `.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000` from this folder. Keep the terminal open and visit **http://127.0.0.1:8000/**. Stop with Ctrl+C. These checks require no AI billing.

Never open the test destinations. Paste them into PluQ, not your browser's address bar.

| Check | Your action | Expected result |
| --- | --- | --- |
| Ordinary QR | Upload `static/demo-ordinary.png` | `example.test`; no obvious indicators, with a clear statement that the website was not verified. |
| Fictional disguise | Select **Disguised URL** | `account-check.test` is the destination. HTTP and the prefix before `@` are explained. |
| Image upload | Upload `static/demo-disguised.png` | Same findings as the pasted disguised URL. No new tab opens. |
| Blank image | Upload an ordinary picture without a QR code | “No QR code found,” rather than a verdict about an old scan. |
| Camera permission denied | Start camera, then deny browser permission | Helpful explanation; image upload and paste remain available. |
| Camera allowed | Show a demo QR card on another screen, start camera and allow permission | Code decodes, camera stops, result appears. Needs real-device verification. |
| Cancel camera | Start camera and select Stop before granting permission | If permission later arrives, the camera is released rather than starting a stale scan. |
| Background tab | Start camera, then switch tabs | Camera stops. Returning does not silently restart it. |
| Invalid QR content | Paste `WIFI:S:demo;P:fictional;;` | Unable to assess as a web URL. No Wi-Fi settings change. |
| Malformed URL | Paste `https://[::1]extra` | Unable to assess; no destination is opened. |
| Unicode domain | Paste `https://faß.test` | IDNA hostname `xn--fa-hia.test` and an internationalized-domain indicator. |
| False-positive check | Paste `https://pineapple.test/hello%20world` | Neither an Apple-brand warning nor an encoding warning solely for the space. Not proof of safety. |
| Explanation modes | Switch Simple / Technical after a disguised scan | Simple: what, why, action. Technical: exact hostname, rule evidence, domain-basis limitation, no reputation check. |
| AI disabled | Select Personalize explanation with AI | Honest rule-based label; no OpenAI request or billing. |
| AI outage simulation | Run the test commands below | Mock timeout/malformed response tests pass; no API credential needed. |
| Clear scan | Select Clear scan | Result and decoded content disappear; input is empty. |

## Confirm the no-click behavior yourself

1. In a desktop browser, open Developer Tools (usually F12), then **Network**. This list shows the browser's requests.
2. Clear the list and select Disguised URL in PluQ.
3. Expect a same-origin `/api/analyze` POST. There must be no request to `account-check.test` or `paypal.com`, and no new page/tab.
4. Click the AI explanation button with AI disabled. Expect only `/api/explain` on the local app.
5. The browser list cannot prove what a backend does. Review `core/analyzer.py` and the network-forbidden automated tests for that separate guarantee. AI's only permitted remote endpoint is explicitly in `core/explanations.py` and is disabled by default.

## Run repeatable checks

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node --test tests/frontend.test.cjs tests/service-worker.test.cjs
node tests/qr-test.cjs
```

If QR fixtures are missing on a fresh checkout, first run `.\.venv\Scripts\python.exe scripts/generate_demo.py` after installing development dependencies. The scripts only generate fictional fixtures locally. Automated camera tests simulate a device, not your physical camera.

## Physical-phone and installation checklist (still unverified)

Use a trusted HTTPS origin after approving an access method in `DEPLOYMENT.md`.

- Test current Safari on an iPhone and Chrome on Android if available. Record phone/browser version and outcome.
- Rear camera preferred; permission denied/allowed; bright and dim light; rotated QR; Stop; tab switching; repeat scans.
- Upload from Photos/Files and confirm camera stops before upload.
- Install/Add to Home Screen; relaunch; repeat camera scan in standalone mode.
- After one successful online visit, use the browser's offline testing mode and reload: cached shell should appear. Decoding can still work, but backend analysis must report failure, not claim a result.
- Restore connectivity, rescan, and check recovery. Refresh/close old tabs after code updates so the new service worker can activate.

Narrow desktop layout testing does not prove mobile Safari compatibility. Do not list the phone checks as passed until you perform them.
