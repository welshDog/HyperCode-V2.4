# BROski Bot Deployment Guide

Complete step-by-step deployment instructions for production environments.

## Prerequisites

### System Requirements
- Ubuntu 20.04+ / Debian 11+ (recommended)
- 2GB RAM minimum (4GB recommended)
- 10GB disk space
- Python 3.11+
- Docker & Docker Compose (for containerized deployment)

### Required Accounts
- Discord Developer Account
- Discord Bot Token
- Discord Server (guild) with admin access

### Optional Services
- MintMe account (for crypto integration)
- OpenAI API key (for AI features)
- Redis (included in Docker setup)

---

## Method 1: Docker Deployment (Recommended)

### Step 1: Install Docker

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

### Step 2: Clone Repository

```bash
# Create app directory
sudo mkdir -p /opt/broski-bot
cd /opt/broski-bot

# Clone repository
git clone https://github.com/welshDog/BROski-Bot.git .
```

### Step 3: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

**Required settings:**
```bash
DISCORD_BOT_TOKEN=your_bot_token_from_discord_dev_portal
DISCORD_GUILD_ID=your_server_id
```

**Get Discord Bot Token:**
1. Go to https://discord.com/developers/applications
2. Create New Application → "BROski Bot"
3. Go to Bot tab → Reset Token
4. Copy token to .env

**Get Guild ID:**
1. Enable Developer Mode in Discord (Settings → Advanced)
2. Right-click your server → Copy ID

### Step 4: Build and Start

```bash
# Build containers
docker-compose build

# Start services
docker-compose up -d

# Verify running
docker-compose ps

# View logs
docker-compose logs -f broski-bot
```

### Step 5: Invite Bot to Server

1. Go to Discord Developer Portal
2. OAuth2 → URL Generator
3. Select scopes: `bot`, `applications.commands`
4. Select permissions:
   - Send Messages
   - Embed Links
   - Attach Files
   - Read Message History
   - Add Reactions
   - Use Slash Commands
   - Manage Roles (if using auto-roles)
5. Copy generated URL
6. Open in browser and invite to your server

### Step 6: Verify Deployment

```bash
# Check bot status
docker-compose logs broski-bot | grep "logged in"

# Should see: "🚀 BROski Bot logged in as BROski Bot#1234"

# Test command in Discord
# Type: /balance
```

---

## Method 2: Systemd Service (Manual)

### Step 1: Install Python

```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip git -y
```

### Step 2: Setup Application

```bash
# Create user for bot
sudo useradd -r -s /bin/false broski-bot

# Create app directory
sudo mkdir -p /opt/broski-bot
cd /opt/broski-bot

# Clone repository
sudo git clone https://github.com/welshDog/BROski-Bot.git .

# Create virtual environment
sudo python3.11 -m venv venv

# Install dependencies
sudo venv/bin/pip install -r requirements.txt

# Configure environment
sudo cp .env.example .env
sudo nano .env  # Edit with your settings

# Set permissions
sudo chown -R broski-bot:broski-bot /opt/broski-bot
```

### Step 3: Create Systemd Service

```bash
sudo nano /etc/systemd/system/broski-bot.service
```

**Service file contents:**
```ini
[Unit]
Description=BROski Bot V3.0
After=network.target

[Service]
Type=simple
User=broski-bot
WorkingDirectory=/opt/broski-bot
Environment="PATH=/opt/broski-bot/venv/bin"
ExecStart=/opt/broski-bot/venv/bin/python /opt/broski-bot/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Step 4: Enable and Start

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable auto-start
sudo systemctl enable broski-bot

# Start service
sudo systemctl start broski-bot

# Check status
sudo systemctl status broski-bot

# View logs
sudo journalctl -u broski-bot -f
```

---

## Post-Deployment

### Database Backup Setup

```bash
# Create backup script
sudo nano /opt/broski-bot/backup-daily.sh

# Add cron job for daily backups at 3 AM
sudo crontab -e
0 3 * * * /opt/broski-bot/scripts/backup.sh
```

### Monitoring Setup

**Prometheus (Docker deployment):**
- Access: http://your-server:9090
- Metrics endpoint: http://your-server:8000/metrics

**Log monitoring:**
```bash
# Real-time logs
tail -f /opt/broski-bot/logs/broski_bot_*.log

# Or with Docker:
docker-compose logs -f broski-bot
```

### SSL/Domain Setup (Optional)

If exposing web dashboard:

```bash
# Install Nginx
sudo apt install nginx certbot python3-certbot-nginx

# Configure reverse proxy
sudo nano /etc/nginx/sites-available/broski-bot

# Get SSL certificate
sudo certbot --nginx -d bot.yourdomain.com
```

---

## Updating the Bot

### Docker Method

```bash
cd /opt/broski-bot

# Pull latest changes
git pull

# Rebuild and restart
docker-compose down
docker-compose build
docker-compose up -d
```

### Systemd Method

```bash
cd /opt/broski-bot

# Pull latest changes
sudo git pull

# Reinstall dependencies (if updated)
sudo venv/bin/pip install -r requirements.txt

# Restart service
sudo systemctl restart broski-bot
```

---

## Troubleshooting

### Bot Not Starting

**Check logs:**
```bash
# Docker
docker-compose logs broski-bot

# Systemd
sudo journalctl -u broski-bot -n 50
```

**Common issues:**
1. **Invalid token** - Check .env DISCORD_BOT_TOKEN
2. **Missing permissions** - Check file ownership
3. **Port conflicts** - Check if ports 6379, 9090 are available
4. **Database locked** - Stop all bot instances

### Bot Online But Not Responding

1. **Check slash commands synced:**
   - View logs for "Commands synced" message
   - May take up to 1 hour for Discord to update

2. **Check bot permissions in server:**
   - Ensure bot has required permissions
   - Check role hierarchy (bot role above managed roles)

3. **Test with prefix commands:**
   - If slash commands fail, try `!balance`

### Performance Issues

**High memory usage:**
```bash
# Check container stats
docker stats broski-bot

# Restart if needed
docker-compose restart broski-bot
```

**Slow responses:**
- Check database size: `du -h database/broski_main.db`
- Run `VACUUM` on SQLite: `sqlite3 database/broski_main.db "VACUUM;"`

---

## Security Checklist

- [ ] .env file has restricted permissions (600)
- [ ] Bot token never committed to git
- [ ] Firewall configured (only needed ports open)
- [ ] Regular backups enabled
- [ ] Database file permissions restricted
- [ ] Bot has minimal Discord permissions needed
- [ ] Logs rotated to prevent disk fill

---

## Rollback Procedure

If update causes issues:

```bash
# Stop bot
docker-compose down  # or: sudo systemctl stop broski-bot

# Checkout previous version
git log --oneline  # Find commit hash
git checkout <commit-hash>

# Restore database backup
cp backups/broski_main_YYYYMMDD_HHMMSS.db database/broski_main.db

# Start bot
docker-compose up -d  # or: sudo systemctl start broski-bot
```

---

## Support

**Issues:** https://github.com/welshDog/BROski-Bot/issues  
**Discord:** https://discord.gg/chyXCC4zj2  
**Docs:** https://github.com/welshDog/BROski-Bot/tree/main/docs

---

*Deployment guide version 1.0 - March 2026*
