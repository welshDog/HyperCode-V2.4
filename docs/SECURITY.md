# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.0.x   | :white_check_mark: |
| 1.x     | :x:                |

## Reporting a Vulnerability

We take the security of HyperCode very seriously. If you discover a security vulnerability, please follow these steps:

1.  **Do NOT open a public issue on GitHub.**
2.  Send an email to `security@hypercode.ai` (or your designated security contact).
3.  Include a description of the vulnerability, steps to reproduce, and any relevant logs.

We will acknowledge your report within 48 hours and provide a timeline for a fix.

## Security Practices

### Secrets Management
*   We use **TruffleHog** in our CI/CD pipeline to scan for committed secrets.
*   `.env` files are strictly gitignored.
*   Production secrets should be injected via environment variables or a secrets manager (e.g., Vault, AWS Secrets Manager).

### Authentication
*   API endpoints are protected via JWT (JSON Web Tokens).
*   Internal services communicate via a private Docker network (`backend-net`).

### Legacy Code Warning
*   The `docs/archive/legacy` folder contains historical code that may reference placeholder API keys or insecure patterns. **Do not use this code in production.**

## License Compliance
This project is licensed under **AGPL v3**. If you modify the source code and run it as a network service, you must disclose your source code, including any security patches applied.
