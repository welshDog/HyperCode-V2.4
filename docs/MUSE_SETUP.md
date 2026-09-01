# 🚀 Muse Code Setup for HyperCode-V2.4

Quick setup guide to get Muse Code running in Docker alongside your agents.

---

## 1️⃣ Add environment variables

Edit your `.env` file in `HyperCode-V2.4`:

```bash
# Muse Code API key (get from developer.meta.com)
MUSE_API_KEY=your_meta_api_key_here

# Contributor tier: true = cheaper (~21x), false = private
MUSE_CONTRIBUTOR_TIER=true

# Project root to mount (default: current directory)
PROJECT_ROOT=/path/to/your/repo

# Data root (matches your other HyperCode services)
HC_DATA_ROOT=/data/hypercode
```

---

## 2️⃣ Create data directory

```bash
mkdir -p /data/hypercode/muse
chmod 755 /data/hypercode/muse
```

---

## 3️⃣ Build the image

```bash
cd HyperCode-V2.4
docker build -t muse-code -f Dockerfile.muse .
```

---

## 4️⃣ Start Muse Code

```bash
docker compose --profile muse up -d muse-code
docker compose logs -f muse-code
```

---

## 5️⃣ Attach to the session

```bash
docker attach muse-code
# or
docker exec -it muse-code bash
muse
```

---

## 6️⃣ Integration with agents-net

The service is already connected to `agents-net`, so it can communicate with:
- MCP Gateway
- Other agents
- Your backend services

---

## 🔧 Troubleshooting

### Auth issues in container

Muse Code's browser OAuth doesn't work well in containers. Use:
- `MUSE_API_KEY` env var (recommended)
- Or pre-authenticate on host, then copy `~/.muse` to the volume

### Permission errors on volume

```bash
chmod -R 755 /data/hypercode/muse
```

### Network not found

```bash
docker network create agents-net
# or
docker compose --profile agents up -d
```

---

**Status**: ✅ Ready to deploy  
**Profile**: `muse`  
**Network**: `agents-net`  
**Data**: `/data/hypercode/muse`

🚀 Let's ship, Bro!
