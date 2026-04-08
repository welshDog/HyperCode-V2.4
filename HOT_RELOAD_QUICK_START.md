# 🔥 Hot-Reload Guide — Docker Compose Watch

Your agent compose files now support **live code sync** via Docker Compose's `develop.watch` feature. Edit agent code and see changes instantly without rebuilding.

## **Quick Start**

### **Option 1: Hot-Reload All Agents (Recommended for Dev)**
```bash
docker compose -f docker-compose.agents.yml up --watch
```

### **Option 2: Hot-Reload with Hyper Agents Stack**
```bash
docker compose -f docker-compose.agents.yml -f docker-compose.hyper-agents.yml up --watch
```

### **Option 3: Standard Up (No Watch)**
```bash
docker compose -f docker-compose.agents.yml up -d
# Agents run normally; code changes require manual rebuild
```

---

## **How It Works**

Each agent service watches these paths:

| Service | Watches | Action |
|---------|---------|--------|
| **coder** | `./agents/coder/` | Sync files to `/app` |
| **agent-x** | `./agents/agent-x/` | Sync files to `/app` |
| **frontend-specialist** | `./agents/01-frontend-specialist/` | Sync files to `/app` |
| **backend-specialist** | `./agents/02-backend-specialist/` | Sync files to `/app` |
| **database-architect** | `./agents/03-database-architect/` | Sync files to `/app` |
| **qa-engineer** | `./agents/04-qa-engineer/` | Sync files to `/app` |
| **devops-engineer** | `./agents/05-devops-engineer/` | Sync files to `/app` |
| **security-engineer** | `./agents/06-security-engineer/` | Sync files to `/app` |
| **system-architect** | `./agents/07-system-architect/` | Sync files to `/app` |
| **project-strategist** | `./agents/08-project-strategist/` | Sync files to `/app` |
| **tips-tricks-writer** | `./agents/09-tips-tricks-writer/` | Sync files to `/app` |

**Plus:** Any change to `./requirements.txt` triggers a full rebuild (dependencies change → image rebuild required).

---

## **Ignored Paths** (No Sync)

These are skipped to avoid bloating syncs:
- `__pycache__/` — Python bytecode
- `.pytest_cache/` — Test cache
- `*.pyc` — Compiled Python files

---

## **Workflow Example**

1. **Start with watch:**
   ```bash
   docker compose -f docker-compose.agents.yml up --watch
   ```

2. **Edit agent code** (e.g., `./agents/coder/main.py`):
   ```python
   # Change some logic
   ```

3. **Save file** → Docker Compose detects change → **Files synced to container** (~1-2s)

4. **Your agent reloads** (if using auto-reload frameworks like Uvicorn)

5. **No rebuild, no container restart** — instant iteration

---

## **Requirements for Hot-Reload to Work**

✅ Your Dockerfiles must:
- Have `WORKDIR /app` or similar
- Support auto-reload (Uvicorn, Nodemon, etc.) or have a reload mechanism
- Avoid caching layer misses (multi-stage builds are fine)

✅ Your agent code must:
- Use a framework that watches for file changes (FastAPI/Uvicorn, Flask, etc.)
- Or implement a reload signal handler

---

## **Troubleshooting**

### **Changes not syncing?**
- Ensure `--watch` flag is present: `docker compose up --watch`
- Check ignored patterns in compose file (might be filtering your files)
- Restart compose: `Ctrl+C` and `up --watch` again

### **Need a rebuild?**
Edit `requirements.txt` → Compose will rebuild automatically, then sync.

### **Want to disable watch for one service?**
Remove the `develop:` block from that service in the compose file.

---

## **Next: Enable Docker Build Cloud**

For even faster builds across your 13+ compose files:

1. Open **Docker Desktop** → **Settings** → **Docker Build Cloud**
2. Sign in with Docker Hub account
3. Enable for your project

This gives you **39x faster builds** on subsequent runs.

---

**Happy coding! 🚀**
