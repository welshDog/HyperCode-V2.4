# 🔧 HyperCode V2.0 — CRITICAL FIXES (Copy-Paste Ready)

**Status:** Ready to execute  
**Time Required:** 4-6 hours  
**Target Completion:** Today EOD  

---

## FIX #1: Resolve Git Merge Conflict (15 minutes)

### Current Status
```
$ git status

On branch main
Your branch and 'origin/main' have diverged,
and have 1 and 4 different commits each

You have unmerged paths:
  (use "git rm" <file>..." as appropriate to mark resolution)
  deleted by them:   Hyper-Agents-Box
  both modified:     THE HYPERCODE
```

### Commands to Run (Copy-Paste in Order)
```bash
# 1. Check current state
git status

# 2. Accept local version of THE HYPERCODE submodule
git checkout --ours "THE HYPERCODE"
git add "THE HYPERCODE"

# 3. Handle deleted Hyper-Agents-Box (if you want to keep it, skip this)
git rm Hyper-Agents-Box  # Only if truly deleted and not needed

# 4. Check status
git status  # Should show fewer unmerged paths

# 5. Complete the merge
git commit -m "fix: resolve submodule conflicts after upgrade

- Accept local THE HYPERCODE version
- Sync with remote changes"

# 6. Rebase to get latest remote changes
git pull --rebase origin main

# 7. Push to remote
git push origin main

# 8. Verify clean state
git status  # Should show "On branch main, working tree clean"
```

### Verification
```bash
# These commands should show no conflicts:
git status
git log --oneline -5  # Should show your merge commit

# Expected output:
# On branch main
# Your branch is ahead of 'origin/main' by 1 commit.
# (use "git push" to publish your local commits)
#
# nothing to commit, working tree clean
```

---

## FIX #2: Audit & Secure .env Files (30 min - 2 hours)

### Step 1: Check if .env is Committed (5 minutes)

```bash
# 1. Check git history for .env files
git log --all --oneline --follow -- "**/.env" | head -10

# If this shows > 0 commits:
#   ❌ Your secrets are exposed! Go to Step 2A (remediation)
# If empty (no output):
#   ✅ Secrets were never committed. Skip to Step 2B (prevention)
```

### Step 2A: IF SECRETS WERE COMMITTED (Remediation - 1-2 hours)

**⚠️ PRIORITY: ROTATE ALL CREDENTIALS IMMEDIATELY**

#### 2A.1: Rotate Credentials (Immediate)
```bash
# 1. Rotate Postgres password
# (Connect to running database and change password)
docker-compose exec postgres psql -U postgres << 'EOF'
ALTER USER postgres WITH PASSWORD 'new-strong-password-32-chars-min';
\q
EOF

# 2. Generate new API_KEY
openssl rand -base64 32

# 3. Generate new JWT_SECRET
openssl rand -base64 32

# 4. Rotate PERPLEXITY API key
# (Log into PERPLEXITY console and generate new key)

# 5. Update .env file with new values
nano .env  # or your editor
# Save and close
```

#### 2A.2: Remove .env from Git History

```bash
# WARNING: This rewrites git history. Coordinate with your team!

# 1. Back up current state
git tag pre-secret-removal  # Safe point to rollback

# 2. Remove all .env files from history
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch .env .env.local' \
  --prune-empty --tag-name-filter cat -- --all

# 3. Force push to rewrite remote history
git push origin main --force-with-lease

# 4. Force push all tags
git push origin --tags --force-with-lease

# 5. Notify team to refresh their local copies
# (They should run: git pull --ff-only)
```

#### 2A.3: Verify Secrets Removed

```bash
# Confirm .env is no longer in history
git log --all --oneline -- "**/.env" | wc -l  # Must return 0

# If still shows > 0:
#   Recheck filter-branch output, may need to re-run with different pattern
```

### Step 2B: IF SECRETS WERE NOT COMMITTED (Prevention - 30 minutes)

```bash
# 1. Check .gitignore
cat .gitignore | grep ".env"

# 2. If .env is NOT in .gitignore, add it
echo ".env" >> .gitignore
echo ".env.local" >> .gitignore
echo ".env.*.local" >> .gitignore

# 3. Verify no .env files tracked
git ls-files | grep .env  # Should return nothing

# 4. Create .env.example template for documentation
cat > .env.example << 'EOF'
# PostgreSQL Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=changeme-generate-strong-password-32-chars
POSTGRES_DB=hypercode

# HyperCode Core Configuration
HYPERCODE_DB_URL=postgresql://postgres:changeme@postgres:5432/hypercode
HYPERCODE_REDIS_URL=redis://redis:6379/0
HYPERCODE_MEMORY_KEY=changeme-generate-base64-32-byte-key

# API Keys
API_KEY=changeme-generate-strong-32-char-key
HYPERCODE_JWT_SECRET=changeme-generate-strong-jwt-secret
PERPLEXITY_API_KEY=sk-your-actual-key-here

# Celery Configuration
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# Environment
ENVIRONMENT=development  # or production
LOG_LEVEL=INFO

# Optional
SENTRY_DSN=  # For error tracking
OTLP_ENDPOINT=http://jaeger:4317  # For tracing
EOF

# 5. Add files to git
git add .gitignore .env.example

# 6. Commit
git commit -m "fix: add .env to .gitignore and create .env.example template

- Prevent future accidental secret commits
- Provide template for new developers
- Document required configuration variables"

# 7. Push
git push origin main
```

### Step 2C: Create Strong .env for Production

```bash
# Generate strong values using openssl
PASSWORD=$(openssl rand -base64 32)
API_KEY=$(openssl rand -base64 32)
JWT_SECRET=$(openssl rand -base64 32)
MEMORY_KEY=$(openssl rand -base64 32)

# Create .env with strong values
cat > .env << EOF
POSTGRES_USER=postgres
POSTGRES_PASSWORD=${PASSWORD}
POSTGRES_DB=hypercode
HYPERCODE_DB_URL=postgresql://postgres:${PASSWORD}@postgres:5432/hypercode
HYPERCODE_REDIS_URL=redis://redis:6379/0
HYPERCODE_MEMORY_KEY=${MEMORY_KEY}
API_KEY=${API_KEY}
HYPERCODE_JWT_SECRET=${JWT_SECRET}
PERPLEXITY_API_KEY=sk-your-actual-key
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
ENVIRONMENT=production
LOG_LEVEL=WARNING
EOF

# Verify .env is NOT tracked
git status | grep ".env"  # Should show nothing

# Test connection
docker-compose up -d postgres
sleep 5
docker-compose exec postgres psql -U postgres -d hypercode -c "SELECT 1;"  # Should return 1 row
```

### Verification

```bash
# Secrets audit passed when:
✅ .env file exists with strong passwords (32+ chars)
✅ .env is in .gitignore
✅ git log --all -- "**/.env" returns 0 commits
✅ All credentials rotated in production systems
✅ .env.example exists as template
```

---

## FIX #3: Fix Ollama Health Check (5 minutes)

### Current Issue
```
hypercode-ollama:
  unhealthy
  Error: "curl": executable file not found in $PATH
```

### Commands to Run

```bash
# 1. Edit docker-compose.yml
nano docker-compose.yml

# 2. Find the "hypercode-ollama" service section (around line 450)
# 3. Locate the healthcheck: section
# 4. Replace this (WRONG):
#    healthcheck:
#      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
#
# With this (CORRECT):
#    healthcheck:
#      test: ["CMD-SHELL", "wget -qO- http://localhost:11434/api/tags || exit 1"]
#      interval: 30s
#      timeout: 10s
#      retries: 5
#      start_period: 60s

# 5. Save and close (Ctrl+O, Enter, Ctrl+X in nano)

# 6. Restart Ollama service
docker-compose up -d hypercode-ollama

# 7. Wait 60 seconds for health check to run
sleep 60

# 8. Verify health status
docker-compose ps | grep ollama
# Should show: "hypercode-ollama ... healthy"

# 9. Test connectivity
curl http://localhost:11434/api/tags
# Should return: {"models":[...]}
```

### Complete docker-compose.yml Entry

Replace your entire `hypercode-ollama` service with this:

```yaml
ollama:
  image: ollama/ollama:latest
  container_name: hypercode-ollama
  restart: unless-stopped
  ports:
    - "127.0.0.1:11434:11434"
  volumes:
    - ./data/ollama:/root/.ollama
  environment:
    - OLLAMA_HOST=0.0.0.0
    - OLLAMA_ORIGINS=*
  healthcheck:
    test: ["CMD-SHELL", "wget -qO- http://localhost:11434/api/tags || exit 1"]
    interval: 30s
    timeout: 10s
    retries: 5
    start_period: 60s
  deploy:
    resources:
      limits:
        cpus: "1.5"
        memory: 4G
      reservations:
        cpus: "0.5"
        memory: 2G
  networks:
    - backend-net
  logging:
    driver: "json-file"
    options:
      max-size: "10m"
      max-file: "3"
  security_opt:
    - no-new-privileges:true
```

### Verification

```bash
# Health check passed when:
✅ docker-compose ps shows "hypercode-ollama ... healthy"
✅ curl http://localhost:11434/api/tags returns JSON
✅ No "curl not found" errors in docker logs
```

---

## FIX #4: Install Missing openai Package (2 minutes)

### Commands to Run

```bash
# 1. Install the package
npm install openai@6.18.0

# 2. Verify installation
npm list openai
# Should show: openai@6.18.0

# 3. Add to git
git add package.json package-lock.json

# 4. Commit
git commit -m "fix: install missing openai dependency

- Root project requires openai for API integration
- Using v6.18.0 (stable release)
- Note: Consider upgrade to v7.x in future sprint"

# 5. Push
git push origin main

# 6. Verify pushed
git log --oneline -1
# Should show your commit message
```

### Verification

```bash
# Installation verified when:
✅ npm list openai shows 6.18.0 or higher
✅ git shows package.json and package-lock.json committed
✅ Can require openai in Node: node -e "require('openai'); console.log('OK')"
```

---

## EXECUTION CHECKLIST

### Pre-Execution (5 minutes)
- [ ] Backup git state: `git tag pre-fixes-backup`
- [ ] Backup project: `cp -r HyperCode-V2.0 HyperCode-V2.0.backup`
- [ ] Verify git status clean: `git status`
- [ ] Check Docker running: `docker ps`

### Execution (4-6 hours)
- [ ] **Fix #1:** Git merge conflict (15 min)
  - [ ] Run git commands in order
  - [ ] Verify: `git status` clean
  
- [ ] **Fix #2:** Audit .env files (30 min - 2 hrs)
  - [ ] Check if secrets committed: `git log --all --oneline -- "**/.env"`
  - [ ] If YES: rotate credentials + filter-branch (1-2 hrs)
  - [ ] If NO: add to .gitignore + create .env.example (30 min)
  - [ ] Create strong .env file
  
- [ ] **Fix #3:** Fix Ollama health check (5 min)
  - [ ] Edit docker-compose.yml
  - [ ] Restart Ollama: `docker-compose up -d hypercode-ollama`
  - [ ] Wait 60 sec, verify health: `docker-compose ps`
  
- [ ] **Fix #4:** Install openai (2 min)
  - [ ] Run: `npm install openai@6.18.0`
  - [ ] Verify: `npm list openai`
  - [ ] Commit and push

### Post-Execution (5 minutes)
- [ ] All fixes complete: `docker-compose ps` (all healthy)
- [ ] All commits pushed: `git log --oneline -5`
- [ ] Run tests: `pytest` (if available)
- [ ] Health check: `curl http://localhost:8000/health`

### Verification (5 minutes)
```bash
# Run these commands to verify all fixes:

echo "=== Git Status ==="
git status  # Should be clean

echo "=== Services Health ==="
docker-compose ps | grep -E "hypercode|ollama|redis|postgres"

echo "=== Secrets in Git ==="
git log --all --oneline -- "**/.env" | wc -l  # Should be 0

echo "=== Ollama Health ==="
curl http://localhost:11434/api/tags

echo "=== OpenAI Package ==="
npm list openai

echo "=== Core API Health ==="
curl http://localhost:8000/health

echo "✅ ALL FIXES VERIFIED!"
```

---

## ROLLBACK PLAN (If Something Goes Wrong)

### Rollback Git Changes
```bash
# If git fixup went wrong:
git reset --hard pre-fixes-backup

# Or if you made a tag:
git checkout pre-fixes-backup
git rebase -i HEAD~5  # Then remove problematic commits
```

### Rollback Docker Changes
```bash
# Restore from backup:
docker-compose down -v
cp -r HyperCode-V2.0.backup/. HyperCode-V2.0/
docker-compose up -d
```

### Rollback .env Changes
```bash
# Restore from backup .env:
cp HyperCode-V2.0.backup/.env .env

# Or recreate clean state:
rm .env
docker-compose restart postgres
```

---

## TROUBLESHOOTING

### Issue: "Cannot resolve merge conflict"
```bash
# Solution:
git merge --abort
git pull --rebase origin main
# Re-run the merge sequence
```

### Issue: "Docker containers won't start after health check fix"
```bash
# Solution:
docker-compose logs hypercode-ollama --tail 20
# Check for actual error (not just health check)
```

### Issue: "npm install fails with permission error"
```bash
# Solution:
sudo npm install openai@6.18.0  # If needed
# Or: npm cache clean --force && npm install
```

### Issue: ".env file not recognized"
```bash
# Solution:
# Make sure .env is in project root (same directory as docker-compose.yml)
ls -la .env  # Should show the file

# Docker Compose needs to load .env:
docker-compose config | grep "POSTGRES_PASSWORD"  # Should show your value
```

---

## TIME ESTIMATE

| Fix | Time | Status |
|-----|------|--------|
| Git conflict | 15 min | ✅ Quick |
| .env audit | 30 min - 2 hrs | ⚠️ Variable (depends on history) |
| Ollama fix | 5 min | ✅ Quick |
| openai package | 2 min | ✅ Quick |
| **TOTAL** | **4-6 hours** | 🟡 Depends on .env audit |

---

## SUCCESS INDICATORS

When you're done, you should see:

```bash
$ docker-compose ps
NAME                      STATUS              PORTS
hypercode-core           Up (healthy)        8000
broski-terminal          Up (healthy)        3000
hyperflow-editor         Up (healthy)        5173
dashboard                Up (healthy)        8088
...
hypercode-ollama         Up (healthy)        11434  ← NOW HEALTHY!

$ npm list openai
hypercode@2.0.0 /path/to/project
└── openai@6.18.0  ← INSTALLED!

$ git status
On branch main
Your branch is up to date with 'origin/main'.
nothing to commit, working tree clean  ← CLEAN!

$ curl http://localhost:8000/health
{"status":"healthy"}  ← ALL GOOD!
```

---

**You've got this! 💪 Execute these fixes and you're ready for production.** 🚀
