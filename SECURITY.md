# Security Policy

## Supported Versions

| Version | Supported |
| --- | --- |
| main branch / GitHub Pages (`https://ym86.github.io/kids-ask-pad/`) | :white_check_mark: |

## Security Architecture & Privacy Design

1. **Client-side API Key Storage**
   - In browser mode (e.g. on GitHub Pages), API keys (Google AI Studio / OpenRouter) are saved strictly in the user's browser `localStorage`.
   - Keys are never uploaded to any intermediate server, analytics, or third party.
   - Outgoing network requests from the browser are restricted by Content Security Policy (CSP) exclusively to the official API endpoints (`generativelanguage.googleapis.com`, `openrouter.ai`, and `ja.wikipedia.org`).

2. **Standalone Server Mode**
   - In local Python server mode (`server.py`), API keys and query logs are stored strictly on the local machine under `data/`.
   - By default, the server binds to `127.0.0.1` and is designed to run behind a local or reverse proxy.

## Reporting a Vulnerability

If you discover a security vulnerability or sensitive information issue in this project:

1. **Do not create a public issue.** Please do not disclose vulnerabilities in public GitHub issues, discussions, or pull requests.
2. Report the vulnerability privately via GitHub Security Advisories:
   - Navigate to the **Security** tab of this repository.
   - Click **Report a vulnerability** to open a private disclosure draft.
3. If private vulnerability reporting is unavailable, please contact the repository owner directly.

### What to Include in Your Report

- A clear description of the vulnerability and its potential impact.
- Step-by-step reproduction instructions or proof-of-concept (PoC).
- Affected environment, browser, or platform details.

We will review reports promptly and take responsible remediation actions.
