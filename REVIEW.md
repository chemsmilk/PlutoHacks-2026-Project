# A short review guide for you and your collaborator

The initial code was AI-assisted. Human review, observed test results, and your design choices should be described honestly to judges. Do not claim an unperformed review or physical-phone test.

## Five functions worth reviewing personally

1. **`analyze()` — `core/analyzer.py`**: splits the address into meaningful parts, normalizes the hostname, and adds observed indicators. Find the `@` fixture and explain why the text before `@` is not the host. Domain normalization uses IDNA, a standard for representing international names with ASCII characters; ambiguous numeric forms are rejected instead of guessed.
2. **`startCamera()` / `frame()` — `static/app.js`**: ask permission, read pixels, decode text, and stop the camera. There is no instruction to navigate to the decoded URL. `stopCamera()` releases the device even if permission arrives late.
3. **`beginInput()` / `analyze()` — `static/app.js`**: each new scan gets a generation number. Only a response with the current number may update the screen. This prevents a slow old scan from replacing the one you just requested.
4. **`explain()` — `core/explanations.py`**: the AI selects an introduction and ordering from fixed choices. A validator rejects missing or invented findings. Only generic finding descriptions leave the backend when AI is explicitly enabled. Technical evidence never comes from AI.
5. **`findings()` — `static/app.js`**: builds the Simple and Technical views using text nodes, not executable HTML. Each simple finding includes what, why, and action. This is a useful place to review wording together without changing security logic.

## Useful questions to answer in your own words

- Why does a warning about an international domain not prove phishing?
- Why does HTTPS alone not establish that a website is trustworthy?
- Why does the scanner refuse to expand shortened links?
- What happens if AI, the server, or camera permission fails?
- Which evidence supports the warning, and what did we deliberately not check?

## The hackathon themes, without overclaiming

- **Build with AI:** optional model-driven prioritization and composition makes verified evidence easier to act on. Currently tested with mocks; live AI remains disabled. This contribution is narrower than unrestricted prose generation and is not a threat-detection model.
- **Protect What Matters:** inspect a QR destination before taking an action that might expose credentials or payment information. Nothing automatically opens the destination.
- **People at the Center:** camera/upload/paste choices, plain-language next steps, technical evidence when wanted, and warnings that acknowledge uncertainty. You and your collaborator own the warning presentation and wording choices; their review is still pending.

A PWA uses one website across computers and phones and can be installed without maintaining separate native apps. Its limitations include browser-dependent camera/install behavior and online backend analysis. With more time: physical-device coverage, carefully designed threat-intelligence integration with privacy controls, broader domain deception analysis, and user-tested AI explanations.
