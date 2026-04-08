# 🔐 Security & Secrets Management — HyperCode V2.0

## Secrets Architecture

```
.env.example          ← Template (safe to commit)
.env                  ← Local overrides (NEVER commit — in .gitignore)
docker-compose.secrets.yml  ← Docker secrets overlay for production
security/             ← Security scanning configs
.secrets.baseline     ← detect-secrets baseline (tracked)
.husky/               ← Pre-commit hooks including secret scanning
```

## Pre-Commit Secret Scanning

Husky runs `detect-secrets` before every commit.

```bash
# Update the baseline after intentional changes
detect-secrets scan > .secrets.baseline

# Audit current secrets
detect-secrets audit .secrets.baseline
```

## Docker Secrets (Production)

```yaml
# docker-compose.secrets.yml overlay pattern
services:
  hypercode-core:
    secrets:
      - openai_api_key
      - anthropic_api_key
      - postgres_password

secrets:
  openai_api_key:
    external: true
  anthropic_api_key:
    external: true
  postgres_password:
    external: true
```

## API Key Rotation Checklist

- [ ] OpenAI API key (`OPENAI_API_KEY`)
- [ ] Anthropic API key (`ANTHROPIC_API_KEY`)
- [ ] PostgreSQL password (`POSTGRES_PASSWORD`)
- [ ] Redis password (`REDIS_PASSWORD`)
- [ ] Grafana admin password (`GF_SECURITY_ADMIN_PASSWORD`)
- [ ] GitHub token (`GITHUB_TOKEN`)
- [ ] Discord bot token (`DISCORD_BOT_TOKEN`)

## .gitignore Key Entries

```
.env
*.env.local
.env.production
secrets/
*.pem
*.key
*.p12
```

## Security Scanning

```bash
# Run bandit (Python security linter)
pip install bandit
bandit -r src/ agents/ backend/ -ll

# Run safety (dependency vulnerability check)
pip install safety
safety check -r requirements.txt
```
