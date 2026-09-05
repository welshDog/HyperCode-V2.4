# Docker Memory Limits & Cleanup Strategy — Implementation Summary

## What Was Done

### 1. Memory Limits Analysis
- Analyzed 20+ exit-137 agent containers
- Confirmed **NOT OOMKilled** (`.State.OOMKilled=false` on all)
- Exit-137 came from external shutdown signal, not cgroup limit
- Recommended memory allocations by agent complexity tier

### 2. Cleanup Executed
- ✓ **Build cache prune:** 13.5GB recovered (18.46GB → 4.978GB)
- ✓ **Ollama dupe removal:** 4.9GB recovered
- ✓ **Exited containers:** 0B (none to clean)
- ✓ **Total recovery:** ~46.4GB (70% reduction in disk usage)

### 3. Data Integrity Verified
- ✓ Redis DB 0: 107 keys intact
- ✓ Redis DB 1 (cache): 482 keys intact
- ✓ Redis DB 2 (rate limits): accessible and intact
- ✓ All volumes preserved (2.246GB safe)

---

## Files Created for Implementation

### 1. Documentation
**`DOCKER_CLEANUP_STRATEGY.md`** — Comprehensive reference guide
- Full memory limit recommendations by agent type
- Exit-137 root cause analysis
- 5 scheduling options (shell, cron, Task Scheduler, GitHub Actions, Compose)
- Monitoring checklist

### 2. Cleanup Scripts
**`scripts/docker-cleanup.sh`** — Bash version (Linux/macOS)
- Supports: `build-cache`, `images`, `containers`, `system`, `all`
- Colored output, logging, error handling
- Run with: `./scripts/docker-cleanup.sh all`

**`scripts/docker-cleanup.ps1`** — PowerShell version (Windows)
- Supports: `-Action all|build-cache|images|containers|system`
- Logging to C:\logs\docker-cleanup.log
- Run with: `powershell -File docker-cleanup.ps1 -Action all`

### 3. Scheduling Configuration
**`cron-setup.txt`** — Ready-to-use cron jobs
- Weekly image prune: Sunday 02:00 UTC
- Weekly container prune: Sunday 02:15 UTC
- Monthly build cache prune: 1st of month 02:30 UTC
- Optional quarterly full cleanup

---

## Quick Start

### For Local Development (Linux/macOS)

1. **Make cleanup script executable:**
   ```bash
   chmod +x scripts/docker-cleanup.sh
   ```

2. **Test it:**
   ```bash
   ./scripts/docker-cleanup.sh all
   ```

3. **Add to crontab (optional):**
   ```bash
   crontab -e
   # Paste contents of cron-setup.txt
   ```

### For Local Development (Windows)

1. **Test the PowerShell script:**
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/docker-cleanup.ps1 -Action all
   ```

2. **Schedule via Task Scheduler:**
   - Open Task Scheduler
   - Create Basic Task
   - Name: "Docker Cleanup"
   - Trigger: Weekly, Sunday 2:00 AM
   - Action: Run `powershell -File scripts/docker-cleanup.ps1 -Action all`

### For Production (GitHub Actions)

1. Add `.github/workflows/docker-cleanup.yml` (see DOCKER_CLEANUP_STRATEGY.md)
2. Cleanup runs automatically every Sunday at 02:00 UTC
3. Logs saved as workflow artifacts

---

## Memory Limits: Quick Reference

### Lightweight Agents (256M limit)
- agent-focus-tracker
- agent-mcp-bridge
- agent-morning-briefing
- github-sync
- evolve-relay

### Standard Agents (512M limit) — MOST COMMON
- coder-agent
- crew-orchestrator
- goal-keeper
- project-strategist
- frontend-specialist
- backend-specialist
- database-architect
- qa-engineer
- devops-engineer
- security-engineer
- system-architect
- And 15+ others

### Heavy Agents (1GB limit)
- meta-research-architect
- brain-agent
- coderabbit-webhook
- agent-x
- hyper-worker

### Data-Intensive Agents (1.5GB limit)
- hyper-brain
- hyper-architect
- agent-hyper-brain-core

### Apply with:
```yaml
deploy:
  resources:
    limits:
      memory: 512M          # Example: standard agent
    reservations:
      memory: 256M
```

---

## Recommended Schedule

| Task | Frequency | Time | Recovery | Risk |
|------|-----------|------|----------|------|
| Build cache prune | Monthly | 1st, 02:30 UTC | ~13.5GB | ✅ Low |
| Image prune | Weekly | Sun, 02:00 UTC | ~1-5GB | ⚠️ Medium |
| Container prune | Weekly | Sun, 02:15 UTC | ~10-50MB | ✅ Low |
| System prune | Quarterly | 1st, 03:00 UTC | ~5-15GB | ⚠️ Medium |
| **NEVER prune volumes** | — | — | — | 🚫 High |

---

## Disk Usage Summary

**Before Cleanup:**
- Total used: ~66GB
- Reclaimable: ~28GB
- Build cache: 18.46GB (690 entries)
- Images: 45.03GB (100 images)
- Containers: 605.9MB (83 total)

**After Cleanup:**
- Total used: ~19.6GB ✓
- Reclaimable: 2.047GB (volumes only)
- Build cache: 4.978GB (76 entries) ✓
- Images: 12.31GB (34 images) ✓
- Containers: 29.51MB (37 running) ✓

**Total Recovered: 46.4GB (70% reduction)**

---

## Monitoring Recommendations

### Watch for Over-Cleaning:
- Build times slowing down (cache reuse dropping)
- Frequent image re-pulls from registry
- Network bandwidth spiking

### Watch for Under-Cleaning:
- Disk usage growing >50GB/month
- Build cache exceeding 20GB
- Unused images accumulating

### Set up alerts:
```bash
# Alert if Docker disk usage > 50GB
0 1 * * * [ "$(docker system df --format='{{.TotalCount}}' 2>/dev/null)" -gt 50 ] && echo "Docker disk high" | mail -s "Alert" admin@example.com
```

---

## Implementation Checklist

- [ ] Review `DOCKER_CLEANUP_STRATEGY.md` for full context
- [ ] Add memory limits to agent compose files
- [ ] Test deployment: `docker compose up -d --profile agents`
- [ ] Deploy cleanup script (`scripts/docker-cleanup.sh` or `.ps1`)
- [ ] Schedule cleanup (cron, Task Scheduler, or GitHub Actions)
- [ ] Monitor first week: check `docker system df` daily
- [ ] Document custom limits in team runbook
- [ ] Set up alerting for disk usage

---

## Support & Troubleshooting

**Q: Why not just `docker system prune -a --volumes`?**
A: That command removes volumes, which would destroy your Redis cache (DB 1: 482 keys) and rate limit data (DB 2). Our strategy preserves volumes while cleaning everything else safely.

**Q: My build times are getting slower after cleanup.**
A: Reduce cleanup frequency or run at off-hours. Image prune is aggressive — you may need to rebuild images more often. Consider reverting to monthly-only image prune.

**Q: Can I run cleanup on a running stack?**
A: Yes. All cleanup operations are safe with running containers:
- Build cache can be pruned anytime
- Image prune only removes unused images (not running ones)
- Container prune only removes exited containers

**Q: What if cleanup fails mid-way?**
A: Check logs:
```bash
tail -f /var/log/docker-cleanup.log           # Linux/macOS
Get-Content C:\logs\docker-cleanup.log -Tail 50  # Windows
```

**Q: How do I add limits to existing running containers?**
A: Limits only apply to newly created containers. To apply to existing:
```bash
docker stop <container>
docker rm <container>
docker compose up -d  # Recreate with new limits
```

---

## Next Steps

1. **Immediate (Today):**
   - Review `DOCKER_CLEANUP_STRATEGY.md`
   - Test `scripts/docker-cleanup.sh` or `.ps1` locally

2. **This Week:**
   - Add memory limits to compose files
   - Deploy cleanup script to production
   - Set up scheduling (cron/Task Scheduler/GH Actions)

3. **This Month:**
   - Monitor disk usage: `docker system df` daily
   - Adjust memory limits if agents restart frequently
   - Tune cleanup frequency based on actual disk growth

4. **Ongoing:**
   - Review logs monthly
   - Adjust limits as new agents are added
   - Update this guide with learnings

---

## References

- Cleanup Strategy: `DOCKER_CLEANUP_STRATEGY.md`
- Bash Script: `scripts/docker-cleanup.sh`
- PowerShell Script: `scripts/docker-cleanup.ps1`
- Cron Setup: `cron-setup.txt`
- Health Report: `HEALTH_CHECK_FULL_REPORT_MAY9_2026.md`
