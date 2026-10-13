# Security Policy

## Reporting a vulnerability

Please report security problems **privately**, not in a public issue. Use GitHub's private vulnerability
reporting: the repository's **Security** tab, then **Report a vulnerability**.

Include what you found, how to reproduce it, and the affected version or commit. You will get an
acknowledgement within a few days. Please allow reasonable time to fix the problem before disclosing it.

## Scope

In scope: the Flask backend, the React frontend, the browser extension, the Docker image and the
deployment files in this repository.

Out of scope: third-party services (Hugging Face, Supabase, Upstash, Vercel, LLM providers) and findings
that need physical access to a user's device.

## What the project already does

- Passwords are hashed with bcrypt; API keys that users store are encrypted at rest (Fernet, HKDF-derived key).
- Production refuses to start with missing, default or short `SECRET_KEY` / `JWT_SECRET_KEY`.
- Row-level security is enabled on the database tables and the API roles have no table grants (migration 0013).
- Dependencies are audited in CI (`pip-audit`, `npm audit`).
- Page text a user saves is treated as untrusted: it is fenced inside LLM prompts, and URLs shown in the UI
  are checked before they are rendered as links.

## Running your own deployment

Set secrets (database URL, Redis URL, `SECRET_KEY`, `JWT_SECRET_KEY`, `LLM_API_KEY`) as host **secrets**, never
as public variables, and rotate any credential that has appeared in a log, a screenshot or a chat.
See [docs/OPERATIONS.md](docs/OPERATIONS.md).
