# 🚀 Paste this as the FIRST message in Claude Code, running in the HyperCode-V2.4 folder on your machine

````text
Hey Claude. I'm Lyndz (@welshDog). I'm dyslexic, autistic and ADHD. Short sentences first, detail only if I ask.
One step at a time. Tell me when something is a win. Never bury a failure.

WHERE WE ARE
A cloud session built "HyperCrew" (a multi-agent crew with Calm Mode, Panic/Focus, Quest Settler, Scribe,
Morning Card) in a sandbox with NO Docker. Everything is committed on branch claude/focused-darwin-ljrs8k
(draft PR #547 on welshDog/HyperCode-V2.4). NOTHING has ever run on Docker. This session is the Docker run.

READ FIRST (in this order, then tell me the 3-line summary before touching anything)
1. CLAUDE.md
2. docs/NEXT_SESSION_HANDOVER_2026-10-02.md   <- the truth about what is and is not proven
3. docs/HYPERCREW_DOCKER_RUNBOOK.md           <- the steps we are about to run
4. WHATS_DONE.md (top 3 entries) and docs/STATUS.md (the HyperCrew block)
If any of these disagree, name the contradiction out loud before acting.

YOUR JOB (in order, stop and show me after each one)
Step 0  Pre-flight: git fetch, checkout claude/focused-darwin-ljrs8k, pull. Check free RAM and `docker ps`.
Step 1  Rebuild ONLY hypercode-core and dashboard. `up -d --no-deps`. NEVER --force-recreate.
Step 2  Confirm migration 023 applied (alembic current = 023, table quest_settlements exists).
Step 3  Is safety-shepherd up? Crew steps now FAIL CLOSED if it is not. Tell me what it answers for a crew run.
Step 4  Run scripts/prove-crew.py phase0, phase1, a REAL `docker restart hypercode-core`, then phase2.
Step 5  Walk the dashboard /ide checklist in the runbook (Morning Card, Pause everything, Focus, /sensory).
Show me the exact PASS/FAIL lines. Do not summarise a failure away.

HARD RULES
- You run the live docker commands yourself, in front of me. No unattended subagents doing live ops.
- STOP RULES (any step): free RAM under 1.2 GB, hypercode-core unhealthy past 5 x 30 s, or any unexpected
  restart -> stop, start no optional services, write down what you saw, ask me.
- Before ANY build: at least 1.5 GB free. After: core healthy and RestartCount 0.
- Do not start services I did not ask for. Do not stop services you did not start.
- Never commit .env or any secret. Never paste a token into chat or a file.
- Do NOT configure a GitHub token or CREW_GITHUB_*. No real PR may be opened. Phase 2 skips the handover gate by
  default; keep it that way unless I say PROVE_APPROVE_HANDOVER=1.
- Do NOT wire the kill-switch into compose or change SAFETY_SHEPHERD_MODE unless I say so. Ask first.
- Never push to main. Only to claude/focused-darwin-ljrs8k. `git fetch` before any push.
- Never skip, disable or loosen a test or a proof check to get green. A red line is information.
- Nothing is "done" until it is committed AND pushed AND you have shown me the proof output.
- Be honest about what you did not verify. "I assumed" is a sentence you must say out loud.

IF SOMETHING FAILS
1. Reproduce it ONCE. Capture the exact error and `docker logs <container> --tail 80`.
2. Find the owning file. Fix the SMALLEST thing that turns that one proof line green. Show me the diff first.
3. Re-run only that step. Commit with a clear message (feat:/fix:/docs:) and push to the branch.
Real bugs are likely here (first Docker run ever). Finding them is the win, not a failure.

THE RUNBOOK IS WRITTEN FROM THE REPO, NOT TESTED
If a command in it is wrong (compose service name, profile, PowerShell vs bash redirects), fix the runbook and
tell me. If my shell is PowerShell: `docker exec -i hypercode-core python - phase0 < scripts/prove-crew.py` does not work there; use
`Get-Content scripts\prove-crew.py -Raw | docker exec -i hypercode-core python - phase0`, or use Git Bash/WSL.

AT THE END (all of it, not just the code)
- Add a WHATS_DONE.md entry: what ran, the exact PASS/FAIL lines, anything that differed from the runbook,
  RAM before/after, RestartCount, what is still unproven.
- Update docs/STATUS.md (HyperCrew block: deployed yes/no) and write docs/NEXT_SESSION_HANDOVER_<today>.md.
- Commit + push to the branch. Tell me the ONE next task in one sentence. Then celebrate.

Start now with: read the four files, give me the 3-line summary, run Step 0. Then wait for my "go".
````

---

**How to use:** open a terminal in `HyperCode-V2.4`, run `claude`, paste everything inside the box above.
