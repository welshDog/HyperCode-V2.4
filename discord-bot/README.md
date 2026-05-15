# 🤖 BROski Discord Bot

MAX-level Discord bot for **HYPERFOCUS z0ne** — wired into HyperCode V2.4.

## ✅ Tier 1 Features
| Feature | Commands |
|---|---|
| 💰 BROski$ Economy | `/balance` `/earn` `/spend` `/give` |
| 🧠 AI Chat | `/broski` `/ask` |
| 🎯 Focus Tracker | `/focus start` `/focus stop` `/focusstats` |
| 📋 Daily Missions | `/missions` + auto-post at 8am UTC |

## 🚀 Quick Start

```bash
# 1. Copy env
cp .env.example .env
# Fill in your values

# 2. Run schema in Supabase SQL editor
# (paste supabase_schema.sql)

# 3. Run via Docker
docker compose -f ../docker-compose.core.yml up discord-bot

# OR local dev
pip install -r requirements.txt
python main.py
```

## 🐳 Add to docker-compose.core.yml

```yaml
discord-bot:
  build: ./discord-bot
  env_file: ./discord-bot/.env
  restart: unless-stopped
  networks:
    - agents-net
  depends_on:
    - fastapi
    - redis
```

## 🔌 FastAPI Endpoints Used
- `POST /ai/chat` — BROski AI chat
- `POST /ai/quick` — Quick Q&A

## 📋 Next: Tier 2
- BROski Pets integration
- XP Leaderboard
- Morning Briefing auto-post
- System health alerts
