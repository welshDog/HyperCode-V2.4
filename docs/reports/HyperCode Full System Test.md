HyperCode V2.4 · Saturday 17 October 2026 · 14:10 to 14:35 BST

# The stack works. The machine under it is out of room.

A read-only test of the host, containers, databases, backups, security, the dashboard, CI and the unit tests. Twelve findings, five of them high. Nothing was changed.

**78**checks pass

**11**need a look

**11**fail

**9**context only

## Fix these first

1. **The PC is out of memory right now**Close Trae and other heavy Windows apps (or at least the extra Trae processes). If you need more room, stop an optional container (fcc-proxy is 196 MB, hyperhealth-api about 164 MB). Do not build or start anything while the guard says AMBER or RED.*2 minutes*
2. **22 of 42 GitHub workflows are broken, including the secret guard and the test suite**One PR that deletes the stray 'on: read' lines in the 22 files and repairs ci-cd.yml, then a staged look at what the revived workflows report. Expect some to fail for real once they run, so do it in two steps rather than all at once. Add a check that rejects duplicate top-level keys so it cannot return.*1-2 hours*
3. **Off-site backups are not leaving the machine**Start Google Drive for Desktop and sign in. The next scheduled run moves everything across with no other change.*2 minutes (you)*
4. **Governor has no usable keys: two of its secrets are empty directories**Delete the two folders, mint governor's agent key with scripts/mint_agent_keys.py governor, create a real governor_operator_key.txt (it must not be the master key, per the overlay comment), then recreate governor with the rollout script's file set.*20 minutes*
5. **The RAM-guard signal has been dead since yesterday evening**Start the task: powershell -File scripts\\ram-guard-task.ps1 -Action start, then check the signal file is fresh. Find out why it stopped (the loop calls WSL, which hangs when WSL is wedged).*5 minutes*

## All twelve findings

Tap a finding to read what I saw, why it matters and what to do. Ordered by severity.

HighThe PC is out of memory right now2 minutes

#### What I found

At 14:35 Windows had 95-190 MB free (guard floor is 100 MB) and Windows memory compression held 3.3 GB. WSL had about 1.47 GB available and a load average of 22-24 (it was 126 at the 13:25 stall). A different set of three containers shows unhealthy on each check: 3 at 14:26 (dashboard, economy consumer, mcp-server), 3 at 14:35 (pets bridge, celery worker, economy consumer). The Windows side is dominated by Trae (20 processes, 581 MB), Claude (307 MB) and the compressed-memory store.

#### Why it matters

This is the condition behind the 10-minute stall at 13:25 (WSL stopped answering, 20 of 38 containers unhealthy). The stack works but has no headroom: any build, restart or test pushes it over.

#### What to do

Close Trae and other heavy Windows apps (or at least the extra Trae processes). If you need more room, stop an optional container (fcc-proxy is 196 MB, hyperhealth-api about 164 MB). Do not build or start anything while the guard says AMBER or RED.

High22 of 42 GitHub workflows are broken, including the secret guard and the test suite1-2 hours

#### What I found

Each of 22 workflow files has a second top-level 'on:' key whose value is just 'read', left by the 15 July commit 'ci: standardize workflow permissions' (3a00f449). GitHub rejects such a file before running anything ('workflow file issue', 0 jobs). The secret-redaction guard has failed all of its last 100 runs (back to 12 October). A 23rd file, ci-cd.yml, is broken differently: its build job needs a job called 'test' that does not exist, and Trivy settings sit inside a setup-python step. PyYAML accepts the duplicate key, so a simple lint does not catch it. The affected files are docker, docs-check, docs-lint, evo-harness, health, hyper-agents-ci, hyper-agents-gate2-e2e, iac-scan, lean-review, no-legacy-paths, performance, playwright-dashboard, promote-dashboards, prune_audit, quality-gate, secret-redaction-guard, security-comprehensive, sse-tests, swarm-pipeline, tests, trivy-scan and trivy-weekly.

#### Why it matters

For about three months most of the project's automated checks have not run, and every push to main shows red. The workflows that do run (CodeQL, image build and push, agent safety suites, secret-file sync, XP reconcile, ecosystem health) are the newer ones.

#### What to do

One PR that deletes the stray 'on: read' lines in the 22 files and repairs ci-cd.yml, then a staged look at what the revived workflows report. Expect some to fail for real once they run, so do it in two steps rather than all at once. Add a check that rejects duplicate top-level keys so it cannot return.

HighOff-site backups are not leaving the machine2 minutes (you)

#### What I found

Google Drive for Desktop is not running or not signed in: drive G: does not exist. The Offsite Copy task last ran at 12:30 and exited 0x2, and its log says 'WAITING: Google Drive folder not found'. The encrypted archives are queued in C:\\HyperCodeBackups (newest 33 MB, 12:30). The watchdog reports this twice a day.

#### Why it matters

Local backups are fine (Postgres dump 32.5 MB at 12:01, stores set at 12:15, both verified), but a disk failure or ransomware would take the backups with the machine.

#### What to do

Start Google Drive for Desktop and sign in. The next scheduled run moves everything across with no other change.

HighGovernor has no usable keys: two of its secrets are empty directories20 minutes

#### What I found

secrets\\agent_api_key_governor.txt and secrets\\governor_operator_key.txt are directories, not files. Docker created them when a bind-mount source did not exist, and inside the governor container /run/secrets/agent_api_key_governor and governor_operator_key are empty folders. The governor log shows only health checks, so nothing complains.

#### Why it matters

Governor cannot authenticate its ledger writes to core as an agent, and operator approvals that need its operator key cannot work. The capability-signing key (a real file) is fine. Governor runs only on the fleet profile, so it is easy to miss.

#### What to do

Delete the two folders, mint governor's agent key with scripts/mint_agent_keys.py governor, create a real governor_operator_key.txt (it must not be the master key, per the overlay comment), then recreate governor with the rollout script's file set.

HighThe RAM-guard signal has been dead since yesterday evening5 minutes

#### What I found

ram-signal/ram.json was last written on 16 October at 18:59 and no pythonw process is running. The scheduled task 'HyperCode RAM Guard Signal' shows result 0x1. throttle-agent therefore reads level UNKNOWN ('signal stale, 70252 s old').

#### Why it matters

throttle-agent is in observe mode, so nothing is paused wrongly, but the host-memory safety net has been blind for about 19 hours, including during the 13:25 stall.

#### What to do

Start the task: powershell -File scripts\\ram-guard-task.ps1 -Action start, then check the signal file is fresh. Find out why it stopped (the loop calls WSL, which hangs when WSL is wedged).

Medium30 dependency PRs are waiting and cannot be validatedafter F2

#### What I found

30 open pull requests, all Dependabot bumps, the oldest #504. Examples: eslint 9 to 10, tailwindcss 3 to 4, mcp 1.28 to 2.3, mypy 1 to 2, pylint 3 to 4.

#### Why it matters

They cannot be trusted or merged while the test workflows (F2) do not run, and several are major-version bumps that need real testing.

#### What to do

Fix F2 first, then triage in groups: patch/minor first, majors one at a time.

Mediumhyperhealth-api returns the Postgres password45 minutes

#### What I found

The 'postgres-db-health' check stores a full database URL, password included, as its target. GET /checks returns it to anyone holding the master key. Confirmed live on 17 October (yes/no test, nothing printed). This was already an open item in my notes.

#### Why it matters

The master key is also held by core, the economy consumer, the Discord bot and the hyperhealth worker, so the password is one request away for each of them.

#### What to do

Mask credentials in the API output, or have the check read DATABASE_URL from the environment instead of storing it. Needs one image rebuild when memory is GREEN.

MediumServices fall back to the public default key if their secret file fails1 hour

#### What I found

Nine running containers still carry 'dev-master-key' in an environment variable (broski-pets-bridge, dashboard, healer-agent, crew-orchestrator, evolve-relay, coder-studio, qa-engineer, coder-agent, safety-shepherd). Today the \*\_FILE secret wins, so it is ignored. The compose files use ${API_KEY:-dev-master-key}, and coder-studio's code defaults to the same literal.

#### Why it matters

If a secret file ever becomes unreadable (the directory problem in F4 is exactly that failure) the service silently reverts to a key that is public in the repo, and it would still look healthy.

#### What to do

Remove the default so compose fails loudly, or add a startup check that refuses to run on the default. Do it service by service with the rollout script.

MediumThe watchdog alerts on deliberate test traffic30 minutes

#### What I found

Two Discord alerts were sent in the last 24 hours. The 13:00 alert on 17 October included 401/403 responses from celery-worker, which was my own test traffic, and from the dashboard before its token was fixed, alongside the real Google Drive problem. The 401/403 detector cannot tell a deliberate negative test from a stale-key caller.

#### Why it matters

Security testing sets off the alarm, and a noisy alarm gets ignored. The 18:00 run may alert again from this test session.

#### What to do

Give test traffic a marker the detector skips, or an allow-list of source containers. Keep running the test with --skip-auth when you only want a health check.

MediumRetired secrets are still on disk1 minute

#### What I found

Five files: jwt_secret.txt.bak-jwt-rotation-20261003 and -20261017, dashboard_service_jwt.txt.bak-jwt-rotation-20261003 and -20261017, and inter_agent_key.old.txt. The 17 October JWT backup holds the secret that was printed into a session; the old shared key is dead on every peer. All are gitignored.

#### Why it matters

They are the files an attacker with disk access would look for, and they no longer have any use once you are happy with the rotation.

#### What to do

Delete them. I did not, because they are the rollback copies.

LowFleet capacity: 9 agents down, 15 not deployedongoing

#### What I found

Dashboard fleet view: 13 to 14 healthy, 5 running, 8 to 10 down, 15 not deployed, 42 total, none crash-looping. Down: backend-specialist, database-architect, devops-engineer, frontend-specialist, goal-keeper, mcp-gateway, mcp-rest-adapter, nemoclaw-agent (and at times others). The Pulse panel shows 0 of 11 agents healthy because only 3 send heartbeats.

#### Why it matters

Expected on an 8 GB machine, but mcp-gateway being down also limits the pets bridge, which was started without its dependencies.

#### What to do

Bring agents back one at a time only when memory is GREEN (F1 first).

LowSmaller thingsvaries

#### What I found

(a) hyperhealth's overall report reads CRIT: grafana-health fails because Grafana is off, and disk-docker-volumes is a known false alarm (it checks /var/lib/docker, which the worker does not mount). I was blocked from disabling it and left it. (b) The Health page's Docker feed needs a browser login. (c) A Docker Desktop extension (kubetoolsca) publishes a port on all interfaces. (d) The economy consumer logged two '->pg FAILED (TimeoutError)' lines during the stall, but the reconcile shows 0 of 328 awards missing. (e) BROskiPets PR #3 is still open and its CI fails on main there too. (f) One untracked file in the repo: the new test script.

#### Why it matters

None of these is urgent.

#### What to do

Handle with the items above; (a) needs your go-ahead.

## Health by area

Bars show passing, warning and failing checks. The numbers read pass / warn / fail.

Host2 / 3 / 1

Docker1 / 0 / 0

Containers4 / 0 / 1

Security18 / 3 / 2

Postgres3 / 0 / 0

Redis4 / 0 / 0

MinIO1 / 0 / 0

Chroma1 / 0 / 0

Backups5 / 1 / 3

Throttle0 / 1 / 2

Dashboard25 / 0 / 0

Fleet2 / 0 / 0

Safety1 / 0 / 0

Services6 / 0 / 0

Economy0 / 1 / 0

CI0 / 1 / 2

Repo2 / 1 / 0

Tests3 / 0 / 0

## What is healthy

**Containers**

39 running, 0 restarts since last recreate, no restart loops, no OOM kills, every container under 85% of its memory limit.

**Postgres**

Accepts queries, 17 connections, 126 MB, 35 tables, core migration 023, no stuck transactions. Wallet 1 holds 7450 XP at level 7; the two wallets total 7640 XP, which matches the dashboard.

**Redis, MinIO, Chroma**

Redis answers, evicts with volatile-lru, uses 4 MB of 512 MB, 0 evictions. MinIO live, Chroma heartbeat 200.

**Backups**

The Postgres backup task last ran at 12:00 with result 0x0: a 32.5 MB dump with its checksum file. The stores backup (Redis, MinIO, Chroma) ran at 12:15 with result 0x0 and a SHA256SUMS file. The restore drills passed on 16 October.

**XP economy**

Reconcile: 328 of 328 awards that landed match the stream, 0 missing, sanity OK. The two timeout log lines did not lose anything.

**Authentication (14 checks)**

Core refuses unauthenticated calls; the re-minted dashboard token works and the old one is dead; the master key is refused on operator routes; the retired shared key and the public default key are refused; healer, pets bridge and evolve-relay each accept exactly the key they should and refuse the others; hyperhealth needs a key.

**Dashboard**

All 11 pages return 200 (the slowest was /agents at 449 ms); 13 of 13 APIs return valid JSON; Pulse is not degraded; crew morning card and panic state load; Safety Shepherd 50 of 50 recent decisions ALLOW.

**Code**

78 pytest checks pass (secret-file sync, XP reconcile, key rotation and minting, pets-bridge key guard), the economy consumer unit tests pass, and all 22 vendored read_secret copies are identical.

**Repo**

On main, level with origin, secrets and .env are gitignored, no secret file is tracked.

## Limits of this test

- It reads state and sends a few requests. It does not start, stop, build or change anything.
- The bad-credential requests ran once at 14:10 and passed. The second pass skipped them so they would not set off the watchdog again.
- Your own Chrome was not connected, so pages were checked over HTTP and with a headless browser.
- Containers flip between healthy and unhealthy under the current memory pressure, so the unhealthy list differs from one check to the next.
- The throttle-agent suite (56 tests) and the dashboard's 264 tests were not re-run, to avoid adding load.
- Running the test adds load on a machine that is already short of memory. Use the script's lighter options when it is.

Every check (109)

| Status | Area | Check | Detail |
| --- | --- | --- | --- |
| WARN | Host | Windows free RAM | 191 MB free of 7974 MB |
| PASS | Host | Disk C: free | 147 GB free of 434 GB |
| PASS | Host | Disk H: free | 1,023 GB free of 1,472 GB |
| FAIL | Host | Google Drive (G:) mounted | G: does not exist: the off-site copy has nowhere to write |
| WARN | Host | RAM guard verdict | VERDICT: AMBER |
| WARN | Host | WSL answers + load average | 1/5/15 min = 22.37 / 15.38 / 17.84 |
| PASS | Docker | Engine answers | 29.8.2 |
| INFO | Containers | Running containers | 39 running, 12 stopped/exited |
| FAIL | Containers | No unhealthy containers | hypercode-dashboard, broski-economy-consumer, hypercode-mcp-server |
| PASS | Containers | No restart loops | none restarting |
| INFO | Containers | Stopped containers | grafana, pyroscope, loki, alertmanager, promtail, cadvisor, node-exporter, tempo, celery-exporter, prometheus-cloud, prometheus, grafana-agent |
| PASS | Containers | No OOM kills | none |
| PASS | Containers | Restart counters | all 0 since last recreate |
| PASS | Containers | Memory use vs limit (\<85%) | all below 85% of their limit |
| WARN | Security | Published ports bound to localhost only | kubetoolsca_krs-docker-extension-desktop-extension-service |
| PASS | Postgres | Accepts queries | 1 |
| INFO | Postgres | Connections / DB size | 17 connections, 126 MB |
| INFO | Postgres | Tables / core migration | 35 tables, alembic 023 |
| PASS | Postgres | BROski wallet readable | 7450 XP, level 7 |
| INFO | Postgres | Per-agent keys minted | 19 keys in agent_api_keys |
| PASS | Postgres | No stuck transactions | 0 idle-in-transaction > 10 min |
| PASS | Redis | Answers PING | PONG |
| PASS | Redis | Eviction policy = volatile-lru | volatile-lru |
| PASS | Redis | Memory vs maxmemory | 4 MB used of 512 MB |
| PASS | Redis | Evictions | 0 keys evicted since start |
| INFO | Redis | XP stream (db1) | 613 awards in broski:xp:log, 335 keys in db1 |
| PASS | MinIO | Liveness | 200 |
| PASS | Chroma | Heartbeat | 200 / HTTPError |
| FAIL | Backups | Task 'HyperCode Backup Watchdog' | last run 2026-10-17 13:00, result 0x1, state Ready |
| FAIL | Backups | Task 'HyperCode Offsite Copy' | last run 2026-10-17 12:30, result 0x2, state Ready |
| PASS | Backups | Task 'HyperCode Postgres Backup' | last run 2026-10-17 12:00, result 0x0, state Ready |
| FAIL | Backups | Task 'HyperCode RAM Guard Signal' | last run 2026-10-15 19:25, result 0x1, state Ready |
| PASS | Backups | Task 'HyperCode Stores Backup' | last run 2026-10-17 12:15, result 0x0, state Ready |
| PASS | Backups | Newest postgres backup in C:\\HyperCodeBackups | backup_20261017_120014.dump, 2.5 h old, 32.5 MB, checksum file present |
| PASS | Backups | Newest stores backup in C:\\HyperCodeBackups | chroma-data.tgz, 2.2 h old, 0.0 MB, checksums in the set's SHA256SUMS |
| WARN | Backups | Discord alerts sent by the watchdog in the last 24 h | 2 alert(s) |
| INFO | Backups | Off-site log (last lines) | 2026-10-17T12:30:13 WAITING: Google Drive folder not found. Encrypted archive(s) are queued in C:\\HyperCodeBac \| 2026-10-17T12:30:13 Start Google Drive for Desktop and sign in; the next run moves them across. |
| PASS | Backups | Watchdog dry run (all its checks) | exit 0; - Core is rejecting calls from services (401/403) - stale or wrong API key? celery-worker -> GET /api/v1/operator/mornin |
| INFO | Security | Auth matrix (deliberate bad requests) | skipped (--skip-auth): those requests would trip the watchdog's 401/403 alert |
| FAIL | Security | Every secrets/\*.txt is a FILE (not a directory Docker made) | directories: agent_api_key_governor.txt, governor_operator_key.txt (a missing bind-mount source was created as an empty folder; the container sees an empty directory) |
| PASS | Security | Secret files non-empty and BOM-free | 63 files ok |
| WARN | Security | Retired-secret backups left on disk | 5 files: dashboard_service_jwt.txt.bak-jwt-rotation-20261003-161330, dashboard_service_jwt.txt.bak-jwt-rotation-20261017-112927, inter_agent_key.old.txt, jwt_secret.txt.bak-jwt-rotation-20261003-161330, jwt_secret.txt.ba |
| PASS | Security | secrets/ and .env are gitignored | secrets/api_key.txt, .env |
| PASS | Security | No secret files tracked by git | secrets/.gitkeep |
| WARN | Security | Containers still carrying the public default key in env | 9: broski-pets-bridge, hypercode-dashboard, healer-agent, crew-orchestrator, evolve-relay, coder-studio, qa-engineer, coder-agent, safety-shepherd (ignored where a \*\_FILE secret wins) |
| FAIL | Security | No password stored in hyperhealth check targets | targets embedding a password: \['postgres-db-health'\] |
| FAIL | Throttle | RAM-guard signal file is fresh (written by the scheduled task) | last written 19.5 h ago: the writer is not running, so throttle-agent reads UNKNOWN |
| FAIL | Throttle | Signal writer process (pythonw ram_guard.py) running | 0 pythonw process(es) |
| PASS | Dashboard | page / | HTTP 200, 515 ms |
| PASS | Dashboard | page /agents | HTTP 200, 410 ms |
| PASS | Dashboard | page /control | HTTP 200, 141 ms |
| PASS | Dashboard | page /docker-zone | HTTP 200, 44 ms |
| PASS | Dashboard | page /flows | HTTP 200, 133 ms |
| PASS | Dashboard | page /grafana | HTTP 200, 124 ms |
| PASS | Dashboard | page /health | HTTP 200, 46 ms |
| PASS | Dashboard | page /ide | HTTP 200, 51 ms |
| PASS | Dashboard | page /mcp | HTTP 200, 46 ms |
| PASS | Dashboard | page /mission | HTTP 200, 70 ms |
| PASS | Dashboard | page /sensory | HTTP 200, 48 ms |
| PASS | Dashboard | API /api/agents | HTTP 200, 879 ms, valid JSON |
| PASS | Dashboard | API /api/broski | HTTP 200, 520 ms, valid JSON |
| PASS | Dashboard | API /api/fleet | HTTP 200, 1075 ms, valid JSON |
| PASS | Dashboard | API /api/health | HTTP 200, 176 ms, valid JSON |
| PASS | Dashboard | API /api/logs | HTTP 200, 181 ms, valid JSON |
| PASS | Dashboard | API /api/metrics | HTTP 200, 2914 ms, valid JSON |
| PASS | Dashboard | API /api/orchestrator | HTTP 200, 182 ms, valid JSON |
| PASS | Dashboard | API /api/pulse | HTTP 200, 666 ms, valid JSON |
| PASS | Dashboard | API /api/safety | HTTP 200, 2970 ms, valid JSON |
| PASS | Dashboard | API /api/tasks | HTTP 200, 3111 ms, valid JSON |
| PASS | Dashboard | API /api/ws-token | HTTP 200, 288 ms, valid JSON |
| PASS | Dashboard | API /api/crew/morning | HTTP 200, 748 ms, valid JSON |
| PASS | Dashboard | API /api/crew/panic | HTTP 200, 91 ms, valid JSON |
| PASS | Dashboard | Pulse not degraded | degraded=None, agents 0/11, XP 7640, coins 95 |
| INFO | Fleet | Agent fleet | 13 healthy, 5 running, 9 down, 15 not deployed, 42 total, crash-looping 0 |
| PASS | Fleet | No crash-looping agents | 0 crash-looping |
| PASS | Fleet | Error rate / DLQ / alerts | error 0%, DLQ 0, firing 0, avg 622.52 ms |
| PASS | Safety | Safety Shepherd decisions | 50 recent, 0 not ALLOW |
| WARN | Throttle | Throttle-agent signal + mode | {"mode": "observe", "signal": {"level": "UNKNOWN", "reason": "signal stale (70252s old, max 120s)", "age_s": 70252.5, "host_free_mb": null, "wsl_avail_mb": null |
| PASS | Services | agent-registry | running healthy |
| PASS | Services | crew-orchestrator | running healthy |
| PASS | Services | safety-shepherd | running healthy |
| PASS | Services | governor | running healthy |
| PASS | Services | healer-agent | running healthy |
| PASS | Services | broski-economy-consumer | running healthy |
| WARN | Economy | Economy consumer log (last 400 lines) | 2 error lines |
| FAIL | CI | Workflow files with a duplicate top-level 'on:' key | 22 of 42 files (GitHub rejects these before running any job): docker.yml, docs-check.yml, docs-lint.yml, evo-harness.yml, health.yml, hyper-agents-ci.yml, hyper-agents-gate2-e2e.yml, iac-scan.yml, lean-review.yml, no-leg |
| WARN | Repo | Working tree clean | 1 changed/untracked files |
| PASS | Repo | On branch | main |
| PASS | Repo | main vs origin/main (ahead/behind) | 0 / 0 |
| FAIL | CI | Latest runs on main | 12 newest runs, 6 failed: secret-redaction-guard.yml, health.yml, ci-cd.yml, trivy-weekly.yml, hyper-agents-ci.yml, quality-gate.yml |
| WARN | CI | Open pull requests | 30 open, 30 of them dependency bumps (oldest #504) |
| PASS | Tests | pytest: secret-env sync, XP reconcile, key rotation/minting, pets-bridge guard | ======================= 78 passed, 1 warning in 42.61s ======================== |
| PASS | Tests | unittest: economy consumer | OK |
| PASS | Tests | vendored read_secret copies identical | 22 files ok |
| PASS | Security | Shared inter-agent key accepted by all enforcing peers | PROBE: no rejections, but some peers do not enforce the key on /\_\_authprobe (marked ?): not proven for them |
| PASS | Security | core refuses an unauthenticated call | HTTP 401 |
| PASS | Security | the re-minted dashboard JWT works | HTTP 200 |
| PASS | Security | the pre-rotation dashboard JWT is dead | HTTP 403 |
| PASS | Security | operator routes refuse the master key | HTTP 403 |
| PASS | Security | the retired shared key is dead | HTTP 401 |
| PASS | Security | the public default key is refused | HTTP 401 |
| PASS | Security | healer refuses the public default key | HTTP 401 |
| PASS | Security | healer accepts the shared key | HTTP 200 |
| PASS | Security | healer /health stays open | HTTP 200 |
| PASS | Security | bridge refuses the shared key (it wants the master key) | HTTP 401 |
| PASS | Security | bridge accepts the master key core sends | HTTP 200 |
| PASS | Security | evolve-relay refuses the master key (it wants the shared key) | HTTP 401 |
| PASS | Security | hyperhealth /checks needs a key | HTTP 422 |
| PASS | Security | hyperhealth /checks accepts the master key | HTTP 200 |