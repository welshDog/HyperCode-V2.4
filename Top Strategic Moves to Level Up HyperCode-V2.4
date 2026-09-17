🎯 Top Strategic Moves to Level Up HyperCode-V2.4
1. Stabilize & Allocate Resources (Foundation)
Your RAM ceiling (N22 from NEXT_TASKS) is the real blocker right now — you're hitting 0.4–0.9 GB free with the full fleet + obs stack, causing OOM-kills, stalls, and silent failures. This needs to be your first move:

Implement docker-compose.memory-limits.yml overlay (already drafted 2026-09-05, never rolled out) across all 40+ agents
Run a real RAM audit: which 5–7 agents use 90% of the memory? Odds are you can identify bloat and trim 20–30% without feature loss
Decision call: Full fleet + obs stack is probably not sustainable on an 8GB box (the 2026-09-03 rule says "don't try"). Run a hard test with the current build to prove either (a) you can fit both with proper limits, or (b) officially accept that obs is a "teardown for rebuild/debug, then restore" workflow, not always-on
2. Ship Card (C) — Wire Safety Into Live Dispatch (Next Task)
You have cards (e)/(a)/(b) built (2026-08-31) but unwired. Card (C) is trivial and unblocks the whole flow:

agents/crew-orchestrator/main.py:524 — add dispatch_capability.needs_strict_path(agent_name) + call the parallel safety_client.check_dispatch() for mutations
Normalize agent_name from multiple formats (backend_specialist ↔ backend-specialist) once at the boundary
This doesn't execute anything yet (Phase 3 is the flip to enforce), just wires the path so the seam exists end-to-end
Impact: Unblocks GitHub Actions billing-recovery work (N14/N15) and proves the whole dispatch-safety stack works for real, not just in unit tests
3. Fix the CI/CD Recovery (Unblock Automation)
Your CI has been dead since April (2026-04-28, quality-gate.yml lost workflow_call). You have 3 pull requests stuck behind N14 (billing lock). Once that clears:

Restore ci-python.yml's workflow_call + 5 inputs (from f2fb97e8)
Fix ~20 corrupted workflow headers (from 3a00f449) — use actionlint after fixing
Quick win: the new agent-safety.yml lane (N12, cards e/a/b) is already built — workflow_dispatch it manually once billing unlocks, verify 71+36+15=122 tests pass, then decide if it gates main
4. Cure the Dashboard Staleness (Process Fix)
You discovered the hard way (2026-09-13, N20) that the dashboard was running a 4-day-old build silently missing SkillFinder and everything else merged since. New habit:

After merging any frontend work, always rebuild dashboard alongside core: docker compose build dashboard hypercode-core
Add a comment to CLAUDE.md's dashboard row documenting this coupling
Consider a Makefile target like make refresh-frontend that does both rebuilds as a single step
5. Complete the LLM Default Model Rotation (Proven Working)
N18 is already live — you rotated to Nemotron and added reasoning: {"exclude": true} on every OpenRouter call. But the discovery:

This same pattern affects every feature using openrouter_chat() (Brain.think(), skills search, potentially others)
You already proved it works with the substring-fallback graceful degradation
Quick verification: scan backend/ for every openrouter_chat() call, confirm all 4 code paths (LLM success, LLM fallback, network timeout, Shepherd block) are tested live with real containers, not mocked
6. Elevate the Skill Discoverability Feature (Go Multiplayer)
You shipped skill search for /ide (2026-09-13, PR#526 merged) — a genuinely useful feature that agents + humans can now discover what each agent does. Expand it:

Backward: Let mission-director use the same skill-search endpoint to auto-suggest task assignments when planning a goal (instead of hardcoding specialist ports + brittle delegation)
Outbound: Expose the skill catalog as a public JSON endpoint (GET /api/v1/skills/catalog) so external tools (IDEs, CLI, other codebases) can discover what HyperCode can do
Internal: Add a @cached_skill decorator to agent methods so they're auto-registered without manual frontmatter (fewer sync bugs with reality)
7. DHI Hardened Images Pilot (Security Lift)
You have a full DHI_PILOT_CHECKLIST.md from 2026-09-07. Phase 0 (Scout baseline) is done (24 CRITICAL / 224 HIGH found). The real win:

Phase 1: Migrate 3 high-traffic images (hypercode-core, hypercode-dashboard, agent-mcp-bridge) to DHI bases in one session
Use get_image_tags tool on python, node, alpine to find the right DHI tags
The tooling is ready; it's just a methodical application
ROI: ~20% disk savings + proven-hardened supply chain for your most critical services
8. Model Runner Idle-Unload + Momentum (Fast Win)
You did the groundwork (2026-09-07, Phase 2 & 3 spike) — Docker Model Runner is verified reachable and speaks Ollama API. Phase 4 cutover is nearly done:

Status check: Is hypercode-ollama still running or has the config swap happened? If still Ollama, swap the shim now (it's a 1-line compose change + model-name reconciliation)
Verified outcome: 1 GB RAM freed (Ollama's old reservation) + 5-min idle-unload lifetime on models
This unblocks Ollama GPU (hypercode-ollama-gpu, --profile gpu) to actually swap in cleanly once Phase 4 finishes
9. End-to-End Mission Control Test (Validation)
You have fleet-controller + governor (Phases 0–2 of the control plane). The missing link is a real, human-guided plan → capability-verified → execution attempt, end-to-end through the real dashboard UI:

Write a TEST_MISSION.md script: goal (e.g., "scale up the brain-agent fleet by 2 replicas")
Hit /missions/propose (LLM plans it) → /missions/review (human approves) → /missions/execute (governor capability + shepherd policy)
Document what should happen at execution time (not yet live — execution.performed is still hard-false), so Phase 3's full execution path has a real, tested endpoint
10. Async/Await Audit (Code Health)
You found (2026-08-23, items 0a/0b) that several agents' code mixes await-missing coroutine calls with sync clients. Prevention:

Run pylint --disable=all --enable=asyncio-misuse on agents/ and backend/
Fix any new instances (you've already patched the known ones)
Add # type: ignore[await-not-called] comments where intentional, so the linter doesn't re-warn
🧭 Why This Order?
Stability first — N22's RAM issue will keep hitting you randomly; fixing it removes the chaos
Seam wiring — Card (C) is 30 mins of coding, unblocks bigger initiatives
Process — CI recovery + dashboard rebuild habit are force multipliers (every future feature lands better)
Feature expansion — Skill discovery already works; amplifying it has immediate developer-experience ROI
Hardening — DHI is security done right, not a hack; 3 services as a proof
Infrastructure — Model Runner cutover is mechanical and frees RAM for other work
Most urgent to start this week: Fix N22 (RAM), then wire card (C). Everything else flows from there.