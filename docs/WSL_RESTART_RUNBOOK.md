# WSL / Docker Desktop restart runbook (controlled, staged)

> Written 2026-10-16 for HYPERFOCUSzone (8 GB RAM, Windows 11 Home, Docker Desktop 4.95, 37 running containers).
> Helper: `scripts/wsl-restart.ps1` (`preflight` / `plan` / `start-stack` / `verify`). Read this whole page once before starting.

## 1. When to use this

The WSL **command channel** is wedged:

| Symptom | What it looked like on 2026-10-16 |
|---|---|
| `wsl -e true` / `wsl -d <any distro> -e true` hangs or fails | `Wsl/Service/0x8007274c` ("connected party did not properly respond") from ~11:50 |
| `ram_guard.py` cannot read WSL | `WSL available: unreadable` -> verdict AMBER -> **builds refused** |
| A pile of hung `wsl.exe` / `wslhost.exe` processes | 10 `wsl` + 8 `wslhost` |
| Host RAM guard signal stuck AMBER | throttle-agent sees AMBER (observe mode: harmless) |

It is **not** memory pressure: `vmmemWSL` was a normal 1.3 GB, containers used 1.6 of 3.9 GB, Docker itself answered
fine (it talks to the engine through its own pipe, not `wsl.exe`). Only the VM-level channel is broken.

**What it blocks:** any image build (the RAM guard refuses), so the economy-consumer fix and the five baked-in agents
(coder-agent, safety-shepherd, coder-studio, evolve-relay, governor) cannot be deployed.

## 2. Read this before touching anything

* **All data lives in one file:** `H:\HyperStation zone\HyperCode\DockerData\DockerDesktopWSL\disk\docker_data.vhdx`
  (**~213 GB**: every image, every volume, including Postgres). The Ubuntu distro disk (24 GB) is on `C:`.
* **NEVER** use Docker Desktop -> Troubleshoot -> *Clean / Purge data* or *Reset to factory defaults*. Either one
  deletes that disk. Restart and "Restart Docker Desktop" are fine.
* **Downtime:** the whole stack is down roughly 20-30 min. Redis pub/sub XP awards published during the window are
  **lost** (pub/sub is not durable): don't `git commit` in the repos while the stack is down.
* **Why not just let Docker restart everything?** Every container has a restart policy, so Docker starts all ~37 at
  once on an 8 GB box (the storm behind the old exit-137 deaths), the `healer-agent` (`always`) starts first and
  "heals" things that are merely not up yet, and `agent-registry` auto-restarts anything it sees "crash". So we stop
  in tiers on the way down and start in tiers on the way up.
* **Why `docker start`, never `compose up`:** `docker start` keeps every container's exact environment. A
  `compose up` recreate re-reads `${API_KEY:-dev-master-key}` from your shell and silently breaks inter-agent auth
  (this cost ~30 min on 2026-10-16; see `docs/AGENT_SECRET_FILES.md`).
* **Pick a quiet window:** not 12:00-12:30 (backups), not around 13:00 / 18:00 (watchdog), no commits planned.

Rough timing: preflight + backups 5 min, shutdown 5 min, Docker/WSL back 3-5 min, staged bring-up 10-15 min,
verify 4 min -> **~30 min** (+15-30 min if you take the optional disk copy).

## 3. Step 0 (optional, zero container impact): try the cheap fix first

The default distro `wsl -e` talks to is Ubuntu-22.04. Terminating **only that** distro does not touch containers:

```powershell
wsl --terminate Ubuntu-22.04
wsl -e true; echo $LASTEXITCODE        # 0 = the channel is back: STOP HERE, no restart needed
```

> **NEVER** `wsl --terminate docker-desktop` (that is the Docker engine VM: instant total outage), and **do not mass-kill
> `wsl.exe` processes**: one of them is Docker Desktop's own long-lived engine host.

Both distros failed on 2026-10-16, which points at the VM-level channel, so expect this to fail. It costs ten seconds.
**Confirmed on the first real run: even `wsl --terminate` timed out**, so go straight to the full restart.

## 4. Preflight (before)

```powershell
cd H:\HYPERFOCUSZONE\HperCore\HyperCode-V2.4

# 4.1 fresh backups, all three must finish OK (watch the logs / status)
foreach ($t in 'Postgres','Stores','Offsite') { Start-ScheduledTask -TaskPath '\HyperCode\' -TaskName "HyperCode $t $(if($t -eq 'Offsite'){'Copy'}else{'Backup'})" ; Start-Sleep 90 }
powershell -NoProfile -File scripts\backup-postgres-task.ps1 -Action status
powershell -NoProfile -File scripts\backup-stores-task.ps1 -Action status
powershell -NoProfile -File scripts\backup-offsite-task.ps1 -Action status      # newest Drive archive should be minutes old

# 4.2 readiness + snapshot of every container (name/image/status/health/restart policy)
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\wsl-restart.ps1 -Action preflight     # must end "READY"

# 4.3 stop the watchdog from alerting about the downtime
Disable-ScheduledTask -TaskPath '\HyperCode\' -TaskName 'HyperCode Backup Watchdog'
```

* `preflight` fails (NOT READY) if a dump is older than 3 h, a container is running that is not in a tier, the snapshot
  is incomplete, disks are low, or the `.wslconfig` swap folder is missing.
* The swap parent folder `H:\HYPERFOCUSZONE\HperCore\wsl` **must exist**, otherwise WSL silently starts with zero swap.
* Expected, harmless warnings: restart=`always` on `healer-agent` and the Docker extension; the 12 exited
  observability containers (9 died of OOM, so Docker may restart them): handled in 5.1.

## 5. Shutdown

Print the exact commands for *this* moment (names come from the live stack, nothing is executed):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\wsl-restart.ps1 -Action plan
```

Run its sections **A -> D in order**:

1. **A. Neutralise auto-start.** `docker update --restart=unless-stopped healer-agent` (so a manual stop sticks) and
   `docker update --restart=no <the 12 exited containers>`. *(They are the observability stack, which the upgrade
   report says must not run by default on this host; leave them `no` until you decide.)*
2. **B. Flush databases.** `redis-cli bgsave` and wait for `rdb_bgsave_in_progress:0`; Postgres `CHECKPOINT`.
3. **C. Stop tier by tier, watchers first** (healer, registry, throttle -> agents -> orchestrator -> core -> data, with
   `-t 60` for Postgres/Redis). Check afterwards: `docker ps` should list only the Docker extension container.
   Postgres log should end with "database system is shut down".
4. **D. Quit Docker Desktop, then the VM:**
   ```powershell
   docker desktop stop
   wsl --shutdown
   wsl -l -v                      # every distro must say Stopped
   Get-Process vmmemWSL -ErrorAction SilentlyContinue      # should be gone
   ```

### 5.1 Optional but recommended once: copy the data disk while nothing is using it

```powershell
$src = 'H:\HyperStation zone\HyperCode\DockerData\DockerDesktopWSL\disk\docker_data.vhdx'
$dst = 'H:\HyperStation zone\HyperCode\DockerData\docker_data.vhdx.pre-restart-20261016'    # ~213 GB; H: has ~1 TB free
Copy-Item -LiteralPath $src -Destination $dst
(Get-Item $src).Length -eq (Get-Item $dst).Length        # must be True
```
It is the only copy that preserves *everything* (volumes + images). Delete it after a day of healthy running.

## 6. Bring-up

```powershell
docker desktop start                       # then wait until `docker info` answers (2-5 min)
wsl -e true; $LASTEXITCODE                 # must be 0   <- the actual fix
wsl -e free -m                             # Swap total must NOT be 0
docker ps                                  # only the extension (+ anything unexpected: stop it) should be up
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\wsl-restart.ps1 -Action start-stack
```

`start-stack` starts tier by tier (`docker start`), waits for each tier to be healthy, and checks the RAM guard between
tiers (it refuses to continue on RED/unanswered). Tiers: 0 proxies+data -> 1 core -> 2 celery -> 3 guards
(fcc-proxy, safety-shepherd, governor) -> 4 crew-orchestrator -> 5 agents -> 6 small agents -> 7 watchers last.
`hypercode-core` needs ~90 s just to import, then migrations: do not restart it while it is "starting".
If a tier stops the run, fix it, then resume: `... -Action start-stack -FromTier 5`.

Then:

```powershell
docker update --restart=always healer-agent                       # restore the policy changed in 5.A
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\wsl-restart.ps1 -Action verify     # must end PASS
Enable-ScheduledTask -TaskPath '\HyperCode\' -TaskName 'HyperCode Backup Watchdog'
powershell -NoProfile -File scripts\backup_watchdog.ps1 -DryRun    # expect only the known economy-consumer 401 until it is rebuilt
Start-ScheduledTask -TaskPath '\HyperCode\' -TaskName 'HyperCode Postgres Backup'
```

`verify` checks: WSL channel + swap, RAM guard verdict, every container that was running in the preflight snapshot is
ready again, nothing that was stopped started by itself, the healer's restart policy, the smoke test, and the watchdog.

### 6.1 Re-apply anything that was only changed LIVE (a restart reverts it)

A stop/start keeps a container's *creation* settings. Anything applied to a running process with no matching container
recreate is lost. Known case: **Redis `maxmemory-policy`** was set live (`CONFIG SET`) on 2026-10-16; after the restart
the watchdog reported `allkeys-lru` again because the container's creation command still said so. Fix permanently by
recreating Redis from the committed compose (data is on a volume; keys and policy `unless-stopped` are preserved):

```powershell
docker compose -f docker-compose.yml up -d --no-deps --no-build --force-recreate redis
docker exec redis redis-cli config get maxmemory-policy        # must say volatile-lru WITHOUT any manual CONFIG SET
```

Only Redis is affected right now, but check `scripts/backup_watchdog.ps1 -DryRun` after every restart: it flags it.

### 6.2 What the first real run looked like (2026-10-16, for planning)

| Phase | Time |
|---|---|
| fresh backups (3 tasks) | ~3 min |
| stop 37 containers in 8 tiers | ~4.5 min (data tier 63 s) |
| `docker desktop stop` + `wsl --shutdown` | ~1 min (both exit 0, VM gone, hung `wsl.exe` pile gone with it) |
| `docker desktop start` -> engine answers | ~35 s |
| `wsl -e true` answered, swap 2048 MB live | immediately after |
| staged `start-stack` (8 tiers) | ~7 min, no tier needed a retry |
| `verify` | ~95 s |
| **total, stack down** | **~14 min** (about half the 30 min estimate) |

Docker started nothing on its own except its own extension container (the `docker update --restart=no` /
`unless-stopped` neutralisation worked). I skipped the optional 213 GB disk copy: only ~65 GB of that file is real
(images 39 GB, build cache 20 GB, volumes 4.8 GB), Postgres/Redis are covered by verified backups, and the small
unbacked volumes were tar-exported to `backups\volumes\` instead (38 MB, ~10 s).

## 7. If something goes wrong

| Problem | Action |
|---|---|
| `wsl --shutdown` hangs > 60 s | Run it again; check `Get-Process vmmemWSL`. Admin shell: `Restart-Service WslService -Force`. Last resort (admin): `Stop-Process -Name vmmemWSL -Force`, then reboot Windows. Postgres will do crash recovery on start; you have fresh dumps. |
| Docker Desktop won't come up | Wait 5 min, then `docker desktop start`; read `%LOCALAPPDATA%\Docker\log\host\*.log`; reboot Windows. **Never** Clean/Purge/Reset. |
| `wsl -e true` still fails after the restart | Reboot Windows (Fast Startup can keep a broken WSL service alive: use *Restart*, not Shut down), then redo 6. |
| A tier will not become healthy | `docker logs <name>`; don't restart-loop it. `agent-registry`/`healer` are not up yet, so nothing is auto-restarting under you. |
| Postgres damaged | Restore the newest `backups\postgres\backup_*.dump` (or `C:\HyperCodeBackups\postgres`, or the encrypted archive in `G:\My Drive\HyperCode-Backups`, passphrase in `secrets\offsite_backup_passphrase.txt`). `scripts/restore_drill_postgres.ps1` shows the exact `pg_restore` flow. |
| Redis / MinIO / Chroma damaged | Restore from `backups\stores\<newest>\` (`scripts/restore_drill_stores.ps1` shows how). |
| Everything is wrong | Stop Docker, `wsl --shutdown`, replace `docker_data.vhdx` with the copy from 5.1, start Docker. |
| Something else started on its own | `docker stop <name>`; check `docker update --restart=no <name>` if it must not return. |

## 8. After a clean restart (what this unblocks)

1. `ram_guard.py --for build` can now READ WSL again, so the verdict is real, but it may read **RED right after a restart**
   (2026-10-16: WSL available 1133 MB vs the 1200 MB stop rule). Cause: before the restart the old VM had pushed ~1 GB of cold
   pages to swap (967 MB used), which made "available" look generous; after a restart everything is resident and swap is
   nearly untouched (92 MB used, ~1.9 GB still free as a buffer), and the full stack's working set is ~2.1 GB of the
   VM's 3.9 GB. It did not settle in 2.5 min. Builds need GREEN (>= 1500 MB), so before building, stop OPTIONAL containers
   by name (never `compose down`) such as the small `agent-*` containers, `evolve-relay`, `skillweaver`, `hyper-brain`,
   `obsidian-watcher`, `github-sync*`, then `docker start` them again afterwards. Re-run `ram_guard.py --for build --wait 120`.
2. Rebuild + swap the economy consumer (code is merged in #602; rollback tag `hypercode-v24-broski-economy-consumer:rollback-20261016`).
3. Rebuild the five baked-in agents for the `read_secret` change (#603), then the coordinated shared-key rollout
   (`docs/AGENT_SECRET_FILES.md`).
4. Delete the optional disk copy after a day of healthy running.

## 9. Do-not list

* `docker compose down`, `up --force-recreate`, or any rebuild **during** the bring-up.
* `wsl --terminate docker-desktop`; killing `wsl.exe` processes en masse.
* Docker Desktop *Clean / Purge data* or *Reset to factory defaults*.
* Starting the observability stack "to see how it looks" (that is what filled 8 GB before).
* Committing in the repos while the stack is down (lost XP awards).
