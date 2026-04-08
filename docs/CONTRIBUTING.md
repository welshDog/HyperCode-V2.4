# Contributing to HyperCode V2.0

**Doc Tag:** v2.0.0 | **Last Updated:** 2026-03-10

Welcome to the HyperCode project! We're building the future of neurodivergent-first AI development tools. This guide will help you get started.

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## 🚀 Getting Started

### Prerequisites
- Docker Desktop (or Docker Engine) with `docker compose`
- Python 3.11+
- Node.js 18+
- Git

### Installation
1. **Clone the repository**
   ```bash
   git clone https://github.com/welshDog/HyperCode-V2.0.git
   cd HyperCode-V2.0
   ```

2. **Setup Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Start the Platform**
   ```bash
   # Start core services
   docker compose up -d

   # Start with agents
   docker compose --profile agents up -d

   # Start with monitoring (Prometheus, Grafana, Jaeger)
   docker compose --profile monitoring up -d

   # Start production stack (includes Nginx Gateway)
   docker compose --profile production --profile agents --profile monitoring up -d
   ```

### Verifying the Launch
To validate your deployment, run the verification script (PowerShell):
```powershell
# Requires production profile for full check
./scripts/verify_launch.ps1
```

## 🛠️ Development Workflow

### Project Structure
- `backend/`: Core API (FastAPI) + Celery tasks
- `dashboard/`: Mission Control UI
- `agents/`: Agent services and shared agent tooling
- `docs/`: Canonical documentation hub
- `docker-compose.yml`: Primary local orchestration (profiles)
- `docker/`, `k8s/`, `monitoring/`: Infrastructure and ops assets

### Coding Standards
- **Python**: Follow PEP 8. Use `black` and `ruff` for formatting.
- **JavaScript/TypeScript**: Use `prettier` and `eslint`.
- **Commits**: Use Conventional Commits (e.g., `feat: add new agent`, `fix: resolve docker loop`).

### Documentation Standards
- Prefer updating canonical docs under `docs/` and linking from root docs rather than duplicating content in multiple places.
- Keep commands consistent: prefer `docker compose ...` (not `docker-compose ...`).
- Avoid secrets in examples: use placeholders like `YOUR_TOKEN_HERE` and document where to obtain them.
- Validate code samples: if a doc adds a command or API example, run it or add a small verification snippet/test.

### Documentation Review
- For any doc change that affects setup, deployment, API usage, or runbooks:
  - Ensure steps work on a fresh clone (or document prerequisites clearly).
  - Confirm links resolve and examples are syntactically valid.
  - If screenshots/diagrams exist, confirm they match current UI/ports/names.

### Testing
Run the test suite before submitting PRs:
```bash
# Run core tests
docker compose --profile agents run --rm hypercode-core python -m pytest -q

# Run agent tests
# (Check specific agent directories)
```

## 🐛 Troubleshooting

### Common Issues
- **Docker Loops/Conflicts**: Ensure you aren't running multiple compose files. Use `docker-compose.yml` with profiles.
- **Port Conflicts**: Check if ports 8000, 3000, 5432, or 6379 are in use.
- **Health Checks**: If a service is unhealthy, check logs: `docker compose logs <service_name>`.

### Reporting Issues
Please use the GitHub Issue Tracker. Include:
- Steps to reproduce
- Expected vs. actual behavior
- Logs/Screenshots

## 🤝 Pull Request Process
1. Fork the repo and create a branch (`feature/your-feature`).
2. Commit your changes.
3. Push to your fork and open a PR.
4. Wait for code review and CI checks.

Thank you for contributing! 🚀
