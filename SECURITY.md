# Security Policy

## Reporting a vulnerability

Please **do not** open a public issue for security or data-protection problems.

Instead, report privately via GitHub's **"Report a vulnerability"** (Security Advisories)
on the repository, or contact the maintainers through the address listed on the
repository profile. We aim to acknowledge reports within a few business days.

Include: affected version/commit, a description, reproduction steps, and impact.

## Scope

Relevant concerns include, but are not limited to:

- **Secret handling** — the app reads `ANTHROPIC_API_KEY` from `.env`/environment only.
  `.env` is gitignored. Report anything that could leak a key (logs, error messages,
  responses).
- **Prompt-injection resistance** — the disclaimer (G1) and scope filter (G2) are
  enforced server-side and must survive injection via user input, retrieved documents,
  or tool output. A bypass is a security issue.
- **PII / data protection** — audit logs hash user IDs and must never contain raw PII
  (see guardrail G8). Report any PII leak. The system is designed **not** to process
  special categories of personal data (Art. 9 GDPR).
- **Citation/number integrity** — guardrails G3 (citation validator) and G4 (number
  provenance) prevent fabricated legal references and figures. A way to smuggle an
  unvalidated citation or figure past them is in scope.

## Operator responsibility

If you deploy OPUS PRIME EX, you are the operator: bind the web UI to trusted networks
only (it defaults to `127.0.0.1`), keep your API key confidential, and ensure your
deployment meets applicable data-protection and professional-law requirements.

## Supported versions

This is an alpha project; only the latest `main` is supported.
