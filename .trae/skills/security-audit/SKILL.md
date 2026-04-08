---
name: security-audit
description: Audit selected code for security vulnerabilities and propose fixes.
---

## Description

This skill reviews the selected code for common security vulnerabilities and suggests specific fixes, including patched code where appropriate.

## When to use

- Reviewing new or risky backend code.
- Working on authentication, authorization, or payment flows.
- Handling sensitive data (user info, tokens, secrets).

## Instructions

1. Read the selected code and identify all entry points and external interactions.
2. Check for:
   - Injection vulnerabilities (SQL, NoSQL, command injection).
   - Cross-Site Scripting (XSS) risks.
   - Missing or weak authentication and authorization checks.
   - Sensitive data being logged or sent in plain text.
   - Use of outdated or insecure dependencies.
3. For each issue:
   - Describe the issue clearly.
   - Assign a severity: High, Medium, or Low.
   - Explain why it is dangerous.
   - Propose a secure fix and show patched code.
4. Verify:
   - Inputs are validated and sanitized (e.g. with Zod).
   - Authorization checks enforce least privilege.
   - Secrets are loaded from environment variables, not hardcoded.
5. Summarize the overall risk level of the selected code and next steps.

## Examples

**Example input (user intent)**

Audit this user profile update endpoint for security issues.

**Example output (high level)**

- List of issues (e.g. missing auth check, potential IDOR).
- Severity per issue.
- Patched endpoint code with proper checks and validation.
