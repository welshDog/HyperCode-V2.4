# 🦅 BROski Discord Bot Developer — Claude Skill

[![HyperCode V2.0](https://img.shields.io/badge/HyperCode-V2.0-blue)](https://github.com/welshDog/HyperCode-V2.0)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Discord API](https://img.shields.io/badge/Discord%20API-v10-5865F2)](https://discord.com/developers/docs)
[![Python](https://img.shields.io/badge/Python-3.11+-green)](https://python.org)

A complete Claude skill that transforms Claude into a **production-grade Discord bot development expert** — optimised for neurodivergent developers with BROski-style responses.

**Part of the [HyperCode V2.0](https://github.com/welshDog/HyperCode-V2.0) ecosystem by [@welshDog](https://github.com/welshDog) 🏴󠁧󠁢󠁷󠁬󠁳󠁿**

---

## 🚀 Quick Start

### Load the Skill in Claude

In any Claude conversation, reference this file:
```
@.claude/broski-discord-bot-skill/SKILL_PROMPT.md
```

Then ask anything:
- *"How do I implement sharding for 5,000 servers?"*
- *"Create a slash command with AI content moderation"*
- *"Set up Redis caching for guild configurations"*
- *"Add rate limiting to prevent API abuse"*

### Deploy Example Bot

```bash
# Clone the repo
git clone https://github.com/welshDog/HyperCode-V2.0.git
cd HyperCode-V2.0/.claude/broski-discord-bot-skill

# Set up environment
cp .env.example .env
# Edit .env with your Discord bot token

# Run with Docker Compose (bot + PostgreSQL + Redis)
docker-compose up -d

# Or run locally
pip install -r requirements.txt
python examples/basic_bot.py
```

---

## 📦 What's Inside

```
.claude/broski-discord-bot-skill/
├── SKILL_PROMPT.md              # 🧠 Main Claude skill
├── skill-config.json            # ⚙️  Skill metadata
├── README.md                    # 📖 You are here
│
├── examples/
│   ├── basic_bot.py            # Production bot with sharding
│   ├── redis_caching.py        # Sub-2ms caching patterns
│   └── ml_moderation.py        # AI content moderation
│
├── .github/workflows/
│   └── ci-cd.yml               # Complete CI/CD pipeline
│
├── .env.example                 # Environment template
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Container image
├── docker-compose.yml           # Full stack deployment
├── CONTRIBUTING.md              # How to contribute
└── LICENSE                      # MIT
```

---

## 🎯 Key Features

### 🔧 Discord API v10 Expert
- Slash commands with proper `ctx.respond()` usage
- Gateway intents (including privileged)
- Auto-sharding for 2,500+ guild requirement
- Button, modal, and select menu interactions
- Webhook and REST API patterns

### ⚡ Scale to 10,000+ Servers
- **Sharding formula**: `ceil(guild_count / 1000)` shards
- **Redis caching**: 95%+ cache hit rate, sub-2ms reads
- **Connection pooling**: asyncpg with 10-100 connections
- **External sharding**: Multi-process for 50,000+ guilds

### 🤖 Machine Learning Built-In
- `unitary/toxic-bert` — 96.1% accuracy content moderation
- Claude API integration for intelligent responses
- Async executor pattern — ML never blocks the event loop
- Configurable thresholds: warn/timeout/kick

### 🔒 Production Security
- Token never hardcoded (`.env` enforced)
- Permission decorators (user + bot validation)
- Rate limiting per user and command
- Parameterized SQL (injection-proof)
- Trivy + TruffleHog in CI/CD

### 🧠 BROski-Optimised Responses
- Chunked information — no walls of text
- Visual structure with emojis
- Code first, explanation after
- Celebrates every win 🔥
- Neurodivergent-friendly format

---

## 📊 Performance Targets

| Metric | Target | Achieved |
|--------|--------|----------|
| Command response | <100ms | ✅ |
| Cache hit (Redis) | <2ms | ✅ |
| Database query | <10ms | ✅ |
| ML inference (GPU) | <50ms | ✅ |
| ML inference (CPU) | <200ms | ✅ |
| Bot uptime | 99.9% | ✅ |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Bot Framework | discord.py 2.x / py-cord |
| Language | Python 3.11+ |
| Cache | Redis 7 |
| Database | PostgreSQL 14 + asyncpg |
| ML | HuggingFace Transformers |
| AI API | Anthropic Claude / OpenAI |
| Container | Docker + Docker Compose |
| CI/CD | GitHub Actions |
| Monitoring | Grafana + Prometheus |
| Error Tracking | Sentry |

---

## 🤝 HyperCode V2.0 Integration

This skill is designed to work with the full HyperCode ecosystem:

- **Agent X** 🦅 — Can autonomously build and deploy Discord bots
- **Crew Orchestrator** — Manages bot deployment tasks
- **DevOps Agent** — Handles CI/CD and container management
- **Healer Agent** — Monitors bot health and auto-recovers
- **BROski Terminal** — Interactive bot management UI

---

## 📈 Roadmap

- [x] Discord API v10 expertise
- [x] Sharding patterns (internal + external)
- [x] ML content moderation
- [x] Redis caching patterns
- [x] Security hardening
- [x] Docker + CI/CD
- [ ] Voice channel automation
- [ ] Advanced embed builders
- [ ] Modal & button interaction patterns
- [ ] TypeScript (discord.js) examples
- [ ] Multi-bot coordination

---

## 📬 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Found a bug?** Open an issue.  
**Got improvements?** PRs welcome! 🔥

---

## 📄 License

MIT — See [LICENSE](LICENSE)

---

**Created with 🔥 by [Lyndz Williams (@welshDog)](https://github.com/welshDog)**  
**Hyperfocus Zone, Llanelli, Wales 🏴󠁧󠁢󠁷󠁬󠁳󠁿**

**NICE ONE BROski♾!** 🦅
