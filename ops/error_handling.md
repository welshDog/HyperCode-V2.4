# 🛡️ BROski Brain Ops — Error Handling Rules

> Version: 1.0.0 | Last updated: 2026-05-31
> Companion to: `ops_taxonomy.json`, `ops_status_template.json`

---

## Rule 1: Chain Doesn't Fail on Individual Step Failure

- GitHub sync fails → continue to briefing generation (you still want today's briefing).
- Discord webhook fails → continue anyway (vault is still updated).
- Vault commit fails → log it, but don't block Discord report.
- **Exception:** If `health_check` fails (Docker/API down), **STOP**. Cannot proceed. All remaining steps are skipped and marked `SKIPPED`.

```
health_check FAILED  → STOP (exit 1)
health_check HEALTHY → continue
  github_sync FAILED → continue (mark FAILED, partial briefing)
    briefing_generation → continue regardless
      vault_commit → continue regardless
        discord_report → runs last, always
```

---

## Rule 2: Graceful Degradation

| Failure Scenario | Behaviour |
|---|---|
| GitHub issues missing | Briefing generated with empty "Open Issues" section |
| Briefing API timeout | Generate from local cache or template stub |
| Vault commit fails | Log it; Discord report still fires |
| Discord webhook down | Log it; vault is still the source of truth |
| 1 repo inaccessible | Sync remaining repos, mark failed repo with `GH_003` |

**Rule:** Always produce the best output you can with what you have. Partial > nothing.

---

## Rule 3: Retry Strategy

| Target | Retries | Backoff | Notes |
|---|---|---|---|
| Network calls (generic) | 3 | 1s → 2s → 4s (exponential) | Covers GH_004, DC_003 |
| Docker API calls | 2 | 1s → 2s | Timing issues, usually self-heal |
| GitHub API (429 / 5xx) | 3 | Respect `Retry-After` header | GH_002 — wait before retry |
| Permission/auth errors | 0 | None | Non-retryable: GH_001, GH_003, DC_001 |

**Non-retryable codes** (fail fast, alert immediately):
`GH_001`, `GH_003`, `DC_001`, `DC_002`, `VC_001`, `VC_002`, `BR_001`, `BR_003`

**Retryable codes** (transient, worth retrying):
`GH_004`, `GH_002`, `DC_003`, `HC_003`

---

## Rule 4: Logging Format

Every step logs to `output/ops.log` (append-only — never overwrite).

```
[TIMESTAMP] [LEVEL] [STEP] [ERROR_CODE] [MESSAGE]
```

**Levels:** `INFO`, `WARN`, `ERROR`, `DEBUG`

**Example log output:**
```
[2026-06-01 08:00:23] [INFO]  [health_check]        HC_000  Starting health check
[2026-06-01 08:00:24] [INFO]  [health_check]        HC_000  Docker daemon responding
[2026-06-01 08:00:25] [INFO]  [health_check]        HC_000  hyper-brain container HEALTHY (uptime 2d 4h)
[2026-06-01 08:00:26] [WARN]  [github_sync]         GH_002  Rate limit hit, retrying in 60s (attempt 1/3)
[2026-06-01 08:00:27] [ERROR] [github_sync]         GH_003  Repo welshDog/BROski not accessible — continuing
[2026-06-01 08:00:28] [INFO]  [github_sync]         GH_000  3/4 repos synced, 47 issues pulled
[2026-06-01 08:00:36] [INFO]  [briefing_generation] BR_000  Briefing generated: 4827 bytes, 5 sections
[2026-06-01 08:00:37] [INFO]  [vault_commit]        VC_000  Committed: a3f2c1e (2 files, +47 -0)
[2026-06-01 08:00:38] [INFO]  [discord_report]      DC_000  Sent to #brain-ops (msg_id: 9876543210)
```

**HC_000 / BR_000 etc. = no-error info code** (step running normally).

---

## Rule 5: Discord Message Format

- **One message per morning** — no spam, no follow-ups unless critical.
- Template:

```
🧠 BROski Brain Ops — {DATE}
{OVERALL_ICON} Overall: {OVERALL_STATUS}

✅ Health Check     — {status} ({duration}s)
{icon} GitHub Sync     — {status} ({repos_ok}/{repos_total} repos, {issues} issues)
{icon} Briefing        — {status} ({size_kb} KB, {sections} sections)
{icon} Vault Commit    — {status} ({commit_hash})
{icon} Discord Report  — SENT ✅

{IF_ERRORS}
⚠️ Needs attention:
• {ERROR_CODE}: {message} → {action}
{/IF_ERRORS}

{IF_ALL_OK}
✅ All systems go. Fresh briefing in vault.
{/IF_ALL_OK}
```

---

## Rule 6: Vault Output Structure

```
$VAULT_PATH/
├── Briefings/
│   └── {YYYY-MM-DD}-briefing.md           ← The daily brain brief
├── GitHub-Inbox/
│   └── {YYYY-MM-DD}-github-sync-report.md ← Issues by repo
└── Ops-Logs/
    ├── {YYYY-MM-DD}-ops-status.json        ← Full machine-readable status (for agents)
    ├── {YYYY-MM-DD}-ops.log                ← Human-readable log (for you)
    └── {YYYY-MM-DD}-dashboard.md           ← Obsidian dashboard note
```

---

## Circuit Breaker Thresholds

| Service | Failure threshold | Recovery timeout |
|---|---|---|
| GitHub API | 5 failures | 5 minutes |
| Docker API | 3 failures | 2 minutes |
| Discord webhook | 3 failures | 10 minutes |
| Briefing API | 3 failures | 5 minutes |

> If circuit is OPEN: skip the step, log `{STEP}_CIRCUIT_OPEN`, report in Discord with recovery ETA.

---

## Implementation Checklist

- [ ] `OperationHandler` class in `hyper_brain_ops.py`
- [ ] Each subcommand uses `execute_with_retry()`
- [ ] Log format matches spec above
- [ ] `ops-status.json` written after every run
- [ ] Circuit breaker state persisted (e.g. Redis or local file)
- [ ] Test: kill Docker → verify chain halts at health_check
- [ ] Test: invalid GitHub token → verify GH_001 fires + no retry
- [ ] Test: slow API → verify GH_004 retries x3 then fails gracefully
