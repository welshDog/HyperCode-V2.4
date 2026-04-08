# 💡 Tips & Tricks #3: Docker Health Checks

Bro, your containers need a pulse! 🩺 If a container is "running" but not "responding," you're in for a world of pain. Let's fix that with **Docker Health Checks**.

---

## 🟢 1. The "Pulse" Concept (Low Complexity)

A **Health Check** is just a command that runs inside your container to see if everything is actually working. It's the difference between a container that's "alive" and one that's actually "working."

- **Why?**: Docker only knows if the process is running. It doesn't know if your app is stuck in an infinite loop or can't connect to the DB.
- **The Result**: If the health check fails, Docker marks the container as `unhealthy`.
- **The Payoff**: Our **Healer Agent** can see this and restart the container automatically. Bro, that's self-healing!

---

## 🟡 2. Basic Implementation (Medium Complexity)

You can add health checks directly in your `Dockerfile` or your `docker-compose.yml`. We prefer **Compose** because it's easier to tweak without rebuilding.

**Copy-Paste This into `docker-compose.yml`**:
```yaml
services:
  my-app:
    image: my-awesome-app:latest
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

**What these do**:
- **test**: The command to run. `curl -f` returns an error if the URL fails.
- **interval**: How often to check (every 30 seconds).
- **timeout**: How long to wait before giving up (10 seconds).
- **retries**: How many times to fail before calling it `unhealthy` (3 times).
- **start_period**: Grace period for your app to boot up (40 seconds).

---

## 🔴 3. Real-World Troubleshooting (High Complexity)

Sometimes the health check itself causes issues. If your check is too heavy, it can eat up CPU and slow down your app.

**Common Scenarios**:
1. **The "Ghost" Failure**: Your app is fine, but `curl` isn't installed in the container.
   - **Fix**: Use a native check like `python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"` or ensure `curl` is in your base image.
2. **The "Too Fast" Failure**: Your app takes 60s to start, but your check starts at 10s.
   - **Fix**: Increase `start_period`. Give that app some space to breathe!
3. **The "Zombie" Network**: Container thinks it's healthy because it can ping itself, but it can't reach the DB.
   - **Fix**: Make your `/health` endpoint actually check the DB connection!

---

## 🎯 4. Success Criteria

You'll know you've crushed it when:
1. Run `docker ps` and see `(healthy)` next to your container status.
2. Stop your database and see the status change to `(unhealthy)` after 3 retries.
3. Check the logs: `docker inspect --format='{{json .State.Health}}' <container_id>`.

**Next Action, Bro**: 
Go to your `docker-compose.yml`, add a health check to one service, and run `docker compose up -d`. Watch that status change! 🚀
