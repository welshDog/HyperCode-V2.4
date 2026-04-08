# 🐶♾️ BROski Bot v4.0 - Enterprise Edition

**Neurodivergent-friendly Discord automation empire** built with Python, discord.py, and Enterprise Architecture.

---

## ✨ Features

- 💰 **Token Economy** - BROski$ rewards, daily streaks, leaderboards
- ⏱️ **Focus Sessions** - Pomodoro timer with hyperfocus bonuses (+200 tokens!)
- 🎯 **Quest System** - Treasure hunts, challenges, achievements
- 🤖 **AI Integration** - Natural language commands via llmcord
- 🏆 **Leveling System** - XP, ranks, auto role assignment
- 💎 **Memory Crystals** - Epic rewards (500+ tokens)
- 🔗 **MintMe Integration** - Real blockchain BROski token airdrops
- 🌐 **REST API** - Secure endpoints for economy and gamification (FastAPI)

---

## 🚀 Quick Start (Enterprise)

### 1. Clone & Setup
```bash
git clone https://github.com/welshDog/BROski-Bot.git
cd BROski-Bot
# Install Poetry if not installed: pip install poetry
poetry install
```

### 2. Configuration
```bash
cp .env.example .env
# Edit .env with your Discord bot token and database details:
# DB_HOST=localhost
# DB_PORT=5432
# DB_NAME=broski
# DB_USER=postgres
# DB_PASSWORD=your_password
```

### 3. Database Migrations
The project uses Alembic for database schema management.
```bash
# Apply migrations to head
poetry run alembic upgrade head

# Rollback one revision
poetry run alembic downgrade -1

# Generate new migration (after model changes)
poetry run alembic revision --autogenerate -m "description"
```

### 4. Run
```bash
# Run Bot
python -m src.main run

# Run API Server (HyperCode Integration)
python -m src.main api
```

---

## 📁 Project Structure

```
src/
├── api/            # FastAPI Routes (Economy, Health)
├── agents/         # AI Agents (Classifier, Code Analyzer)
├── cogs/           # Discord Extensions (Economy, Focus, etc.)
├── config/         # Settings & Logging
├── core/           # Core Logic (Database, Exceptions)
├── integrations/   # External APIs (MintMe)
├── models/         # Database Models
├── repositories/   # Data Access Layer
├── services/       # Business Logic Layer
└── utils/          # Utilities
```

---

## 📋 Commands

### 💰 Economy
- `/balance [@user]` - Check token balance
- `/daily` - Claim daily reward (streak bonus!)
- `/give @user amount` - Gift tokens
- `/leaderboard` - Top earners

### ⏱️ Focus & Productivity
- `/focus project` - Start hyperfocus session (+50 tokens)
- `/focusend` - End session (+200 tokens base reward!)

### 🎯 Quests
- `/quests` - View active quests
- `/achievements` - Your unlocked achievements

---

## 🔌 API & Integration

BROski Bot exposes a REST API for integration with **HyperCode V2.0**.

- **Base URL:** `http://localhost:8000`
- **Docs:** `/docs` (Swagger UI)
- **Endpoints:**
  - `GET /economy/balance/{user_id}`
  - `POST /economy/redeem`
  - `POST /economy/transfer`

---

## 🐳 Docker Deployment

```bash
docker-compose up -d
docker-compose logs -f broski-bot
```

---

## 🛠️ Tech Stack

- **Runtime:** Python 3.11+
- **Bot Framework:** discord.py 2.x
- **API Framework:** FastAPI
- **Database:** PostgreSQL (SQLAlchemy + AsyncPG)
- **Dependency Management:** Poetry
- **Monitoring:** Prometheus + Grafana

---

## 🧠 Built for Neurodivergent Developers

This bot is specifically designed with ADHD and dyslexia in mind:

- ✅ Clear visual feedback with embeds
- ✅ Quick wins and dopamine rewards
- ✅ Streak systems for motivation
- ✅ Hyperfocus session tracking
- ✅ No walls of text - bite-sized info

---

## 👨‍💻 Author

**Lyndz Williams** (@welshDog)  
Welsh Indie Developer | Llanelli, Wales 🏴  
Building accessible AI tools for neurodivergent creators

---

## 📝 License

MIT License - Built with 🧠 and ♾️

---

**HYPERFOCUS MODE ACTIVATED** 🔥🐶
