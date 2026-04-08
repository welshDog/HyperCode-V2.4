# 💡 Tips & Tricks #8: Security Auditing & Secret Management

Bro, a "Soulful" agent is an ethical one, and an ethical agent doesn't leak secrets. 🛡️ In HyperCode, we handle sensitive API keys and agent auth with extreme care. Let's harden your stack.

---

## 🟢 1. The Secure `.env` Pattern (Low Complexity)

Never, ever hardcode your keys. Use a `.env` file and ensure it's in your `.gitignore`.

**Copy-Paste: Secure `.env` Template**:
```bash
# --- 🛡️ HYPERCODE CORE SECRETS ---
PERPLEXITY_API_KEY=sk-ant-your-key-here
OPENAI_API_KEY=sk-your-key-here
HYPERCODE_JWT_SECRET=use-a-long-random-string-here

# --- ⚙️ DATABASE SECRETS ---
POSTGRES_PASSWORD=don-not-use-password123
MINIO_ROOT_PASSWORD=another-strong-password
```

- **Why?**: If you push your keys to GitHub, bots will steal them in seconds and run up your bill. Bro, that's a bad day.
- **Pro Tip**: Use a tool like `1Password` or `Bitwarden` to generate and store these.

---

## 🟡 2. Agent-to-Agent Auth (Medium Complexity)

Our agents talk to each other. We use **API Keys** or **JWT Tokens** to make sure only *our* agents can trigger sensitive missions.

**Copy-Paste: Simple Auth Middleware for `agent.py`**:
```python
from fastapi import Header, HTTPException

async def verify_agent_token(x_agent_key: str = Header(...)):
    # Check against our master key stored in env
    if x_agent_key != os.getenv("HYPERCODE_API_KEY"):
        raise HTTPException(status_code=403, detail="Bro, you're not on the list.")
    return True

@app.post("/execute", dependencies=[Depends(verify_agent_token)])
async def secure_task():
    return {"status": "authenticated_and_ready"}
```

- **Benefit**: Prevents unauthorized entities from hijacking your agents.
- **Rule**: Every agent in the HyperCode ecosystem should check this key.

---

## 🔴 3. Env Leaks & Docker Secrets (High Complexity)

Sometimes environment variables leak through logs or debug endpoints. 

**The Risk**: 
- **Log Leaks**: An agent crashes and prints the entire `os.environ` to the console.
- **Container Inspect**: Someone with access to the Docker socket runs `docker inspect` and sees every plain-text key.

**The Fix: Docker Secrets (Production Style)**:
Instead of passing keys via `environment:` in Compose, use `secrets:`.

**Copy-Paste: `docker-compose.yml` Secrets**:
```yaml
services:
  hypercode-core:
    secrets:
      - PERPLEXITY_key
secrets:
  PERPLEXITY_key:
    file: ./secrets/PERPLEXITY_key.txt
```

- **Why?**: Secrets are mounted as files in `/run/secrets/`, which is much harder to leak via environment dumps.

---

## 🎯 4. Success Criteria

You've officially hardened your system when:
1. `git status` shows `.env` is ignored.
2. An agent request without an `X-Agent-Key` header returns a `403 Forbidden`.
3. Your logs are clean and contain zero traces of your actual API keys.

**Next Action, Bro**: 
Run a quick audit: `grep -r "sk-" .` in your project root. If you see an API key in any file other than `.env`, move it immediately! 🚀
