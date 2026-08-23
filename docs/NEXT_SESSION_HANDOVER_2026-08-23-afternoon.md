# 🏁 Session Handover — 2026-08-23 afternoon · "Item 0b Closed for Real, Full Chain Proven Live"

> Continues from `docs/NEXT_SESSION_HANDOVER_2026-08-23.md`, which paused
> item 0b's rollout mid-way (2 of 7 specialists rebuilt, terminal restart
> for a Claude Code update). This session finished it — all 7, live-verified
> end-to-end, no open engineering items left from this thread.

---

## ⚡ TL;DR

1. **Item 0b closed.** Rebuilt + recreated the remaining 5 specialists
   (`database-architect`, `qa-engineer`, `devops-engineer`,
   `security-engineer`, `system-architect`). All 7 specialists now confirm
   `AGENT_MODEL` reads `None` (falls through to the live-valid default)
   instead of the retired `claude-3-5-sonnet-20241022`.
2. **New bug caught mid-rollout, fixed same session**: `security-engineer`/
   `system-architect` define an explicit `image:` tag override
   (`hypercode-security-engineer:latest`/`hypercode-system-architect:latest`
   — no `v24`) that doesn't match the `hypercode-v24-<name>` convention the
   other 5 use (they have no `image:` field, so Compose's own
   `<project>-<service>` default naming happens to equal that convention).
   Building the first pass under the uniform tag silently produced an
   orphan image for those 2 — `docker compose up --force-recreate` (no
   `--build`) just reused the old stale image under the real tag. Caught by
   re-checking `AGENT_MODEL` after recreate rather than trusting the step
   alone. **Always check a compose service's own `image:` field for a tag
   override before assuming uniform naming.**
3. **Full delegation chain proven live, not just the env var.** Real
   `project-strategist` `/execute` call → real 4-task structured plan
   (`status: "planned"`) → `delegate_tasks()` fired real HTTP calls to
   `backend-specialist` (×2), `qa-engineer`, `devops-engineer` — all
   `200 OK`, each producing genuine, substantive LLM-generated
   implementation plans (real code, real reasoning), confirmed in each
   specialist's own container logs. This is the exact path item 0b's bug
   used to break with a generic "Connection error."
4. **`project-strategist`'s known `Exited (255)` recurred again**, no error
   in logs before shutdown — same unexplained signature as before.
   `docker start project-strategist` recovered it cleanly, no rebuild
   needed (bind-mounted). Root cause still not identified — see "Carried
   Forward" below.
5. **Docs synced, committed, pushed**: `WHATS_DONE.md` (new entry),
   `docs/NEXT_TASKS.md` (item 0b row → ✅ resolved, header updated).
   Commit `65cc8a99`, Evo Harness gate passed 26/26 before push.
6. **Separate, unrelated**: added an idea to `Brainstorm HyperCode OFF Your
   Laptop` (untracked scratch doc, not part of the repo's doc set) — flagged
   that `data-net` is `internal: true` with zero host route today, proposed
   Tailscale mesh over the doc's own Docker Swarm suggestion, called out the
   `HYPERCODE_DB_URL`/`DATABASE_URL` + `HYPERCODE_REDIS_URL`/`REDIS_URL`
   dual-naming trap (127 files total) that would bite a real host split, and
   flagged that `healer-agent`/`throttle-agent` can't move to Oracle Cloud
   without losing their whole purpose (they proxy *this host's* Docker
   socket via `docker-socket-proxy-healer`). Not an engineering task, no
   code touched — purely a doc contribution, evaluate independently if
   Bro wants to act on the cloud-split idea.

---

## 🔴 What's Actually Left

**Nothing from item 0b or N1/N2/N4/N7/0a — all closed, all live-verified.**
The only carried-forward item with no owner is the recurring
`project-strategist` `Exited (255)` below.

---

## 📌 Carried Forward, Unchanged

- **`project-strategist`'s `Exited (255)`** — recurred a third time this
  session (previously: found 2026-08-22 afternoon, recurred once more
  before the 2026-08-22 night full-fleet restart). No error visible in logs
  before shutdown, all three times. `docker start` always recovers it
  cleanly (bind-mounted, no rebuild needed) but the actual trigger is still
  unknown. Worth a real investigation next time it happens — catch it
  in the act (watch `docker events` or add explicit exit-signal logging)
  rather than just restarting past it again.
- `:memory:.ses` stray file in `frontend-specialist`/`backend-specialist`'s
  bind-mounted directories (found 2026-08-23 midday, not chased) — worth a
  look if it recurs on the other 5 specialists now that they've been
  recreated too.
- N5 — `docs/STATUS.md`'s "Agent Fleet — 25 Total" table is still stale
  (wrong ports, predates the 08-19/08-20 reconciliation). Banner-only fix,
  still needs a real pass.
- The P1-P3 dashboard playtest backlog and "This Week" list in
  `docs/NEXT_TASKS.md` — untouched this session, not raised.

---

## 🔑 Key Facts (don't re-derive)

| Fact | Detail |
|---|---|
| Specialist agent image tags | 5 of 7 (`frontend-specialist`, `backend-specialist`, `database-architect`, `qa-engineer`, `devops-engineer`) have no `image:` field in compose — Compose's default `<project>-<service>` naming equals `hypercode-v24-<name>`. The other 2 (`security-engineer`, `system-architect`) have an **explicit** `image:` override with no `v24` in the name. Always grep the service block for `image:` before rebuilding by hand. |
| `AGENT_MODEL` verification | `docker exec <name> python3 -c "import os; print(os.environ.get('AGENT_MODEL'))"` should print `None` for all 7 specialists now — confirmed live. |
| Full-fleet health | Zero unhealthy containers across all running (58 at last count with the partial file set used this session — the canonical launch command counts 25 agents + supporting infra higher). |

---

## 🎯 One Next Task

Nothing urgent queued. If picking something up: investigate
`project-strategist`'s recurring `Exited (255)` properly (it's now happened
3 times with zero logged cause), or evaluate the Tailscale cloud-split idea
added to the brainstorm doc if Bro wants to actually pursue getting
HyperCode off the laptop.

---

> 🐶♾️ Built by @welshDog · Llanelli, Wales
