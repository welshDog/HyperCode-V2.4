# Security

## Reporting

If you believe you’ve found a security issue, please open a GitHub issue with minimal reproduction details, and avoid posting secrets or tokens.

## Secret Handling

- Do not commit `.env` files.
- Use `.env.example` as the template and keep real values in your local environment or secret store.
- Rotate keys immediately if a secret ever lands in git history.

## Security Artifacts

- [security/](security/) contains security audit artifacts and reports.

