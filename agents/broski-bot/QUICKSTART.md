# 🚀 BROski Bot Quick Start

**Get your bot running in 10 minutes!**

## ⚡ Super Fast Setup (Docker)

### 1️⃣ Prerequisites Check
```bash
# Check Docker installed
docker --version
docker-compose --version

# If not installed, run:
curl -fsSL https://get.docker.com | sh
```

### 2️⃣ Clone & Configure
```bash
# Clone repository
git clone https://github.com/welshDog/BROski-Bot.git
cd BROski-Bot

# Setup environment
cp .env.example .env
nano .env  # Add your Discord token
```

**Get Your Discord Token:**
1. Go to https://discord.com/developers/applications
2. New Application → "BROski Bot"
3. Bot tab → Reset Token → Copy
4. Paste in `.env` as `DISCORD_BOT_TOKEN=paste_here`

### 3️⃣ Launch
```bash
docker-compose up -d
```

**That's it!** 🎉

### 4️⃣ Invite to Server
1. Discord Developer Portal → OAuth2 → URL Generator
2. Select: `bot` + `applications.commands`
3. Permissions: Send Messages, Embed Links, Use Slash Commands
4. Open generated URL → Invite to your server

### 5️⃣ Test
Type in Discord: `/balance`

---

## 🐍 Python Setup (No Docker)

```bash
# Install Python 3.11
sudo apt install python3.11 python3.11-venv -y

# Clone & setup
git clone https://github.com/welshDog/BROski-Bot.git
cd BROski-Bot
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
nano .env  # Add your token

# Initialize database
sqlite3 database/broski_main.db < database/schema.sql

# Run
python bot.py
```

---

## 🎮 First Commands to Try

```
/balance        - Check your tokens
/daily          - Claim daily reward
/focus 25       - Start 25-min focus session
/focus-stop     - Complete session
/rank           - Check your rank
/leaderboard    - See top members
```

---

## 📊 Monitoring

- **Logs:** `docker-compose logs -f broski-bot`
- **Prometheus:** http://localhost:9090
- **Database:** `database/broski_main.db`

---

## 🆘 Troubleshooting

**Bot offline?**
```bash
docker-compose logs broski-bot | grep ERROR
```

**Commands not working?**
- Wait 5-10 min for Discord to sync slash commands
- Check bot has permissions in server
- Try prefix command: `!balance`

**Need help?**
- Discord: https://discord.gg/chyXCC4zj2
- Issues: https://github.com/welshDog/BROski-Bot/issues

---

## 📚 Next Steps

1. Read [COMMANDS.md](docs/COMMANDS.md) - All available commands
2. Read [DEPLOYMENT.md](docs/DEPLOYMENT.md) - Production setup
3. Read [ARCHITECTURE.md](docs/ARCHITECTURE.md) - How it works
4. Join Hyperfocus Zone Discord for support

**Happy coding!** 🐶♾️
