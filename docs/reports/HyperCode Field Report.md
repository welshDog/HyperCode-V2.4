HyperCode V2.4 · Saturday 17 October 2026

# Seventeen agents live, nothing on fire.

A snapshot of the stack as the dashboard sees it, taken at 12:24 BST. Every figure below names the dashboard endpoint it came from.

**17**agents live of 42/api/fleet · healthy 12 + running 5

**0%**error rate, dead-letter queue 0/api/metrics · 16 req/min, 206 ms average

**50/50**Safety Shepherd decisions allowed/api/safety · latest 50 events

**Lv 7**BROski Legend, 7,635 XP, 95 coins/api/broski

## The fleet, agent by agent

10 agents are down on purpose or by memory limits, 15 are not deployed. The machine has 8 GB, so the rest wait their turn.

healthy running down not deployed

/api/fleet · generated 12:24 BST

## The dashboard, live

## What changed this weekend

### Fri 16 Oct

- Postgres, Redis, MinIO and Chroma now back up every day, copied to C: and encrypted into Google Drive. Restore drills passed.
- Docker was restarted safely using a written runbook, then the BROski$ economy consumer came back on.
- 63 lost BROski$ awards were recovered (+660 XP). A watchdog now flags any new gap.
- Agent keys moved toward secret files instead of environment values.

### Sat 17 Oct

- One shared key now lives in a single secret file for all nine agents that use it. The public default key no longer opens the healer.
- The JWT signing secret was rotated and the dashboard token re-minted, which brought the Studio morning card back.
- Dashboard polling and scrolling fixes were merged, and the rotation script now understands the file layout.
- Hung health probes are now capped. They had piled up to over 1 GB of memory.

## Waiting on you

**Decide on BROskiPets PR #3**Its CI fails on main too (missing supabase module). Merging it makes the evolve-relay rebuild source safe.

**Delete the old JWT secret backup**secrets/jwt_secret.txt.bak-jwt-rotation-20261017-112927 still holds the retired secret. It is gitignored.

**Re-mint the dashboard token before 16 November**The updated rotation script does it, and will be its first full run.

**Pick which down agents to bring back**hyperhealth-api, broski-pets-bridge and nemoclaw-agent matter most. Start them with the secrets overlay so they get the file key.

Sources: the dashboard's own routes at 127.0.0.1:8088 (/api/fleet, /api/metrics, /api/safety, /api/broski) and live screenshots of the same pages, all captured 12:24 BST on 17 Oct 2026.

Static snapshot. The numbers do not update after publishing.