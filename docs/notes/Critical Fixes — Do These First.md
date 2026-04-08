🚨 Critical Fixes — Do These First
Fix 1 — Port Confusion (Healer vs System Architect)
system-architect claims 8008 internally

But healer-agent maps 8010 → 8008 in compose

Fix: Healer health check = localhost:8010, NOT 8008

System Architect health check = internal only via Orchestrator

Fix 2 — DevOps Agent Needs Docker Socket
The DevOps agent is missing the Docker socket mount. Add this to its service in docker-compose.yml:

text
volumes:
  - //./pipe/docker_engine://./pipe/docker_engine  # Windows Docker Desktop
  # OR on Linux:
  # - /var/run/docker.sock:/var/run/docker.sock
security_opt:
  - no-new-privileges:true
Fix 3 — "Agent X" Is a Myth in Compose
Remove "validate Agent X" from the Phase Map checklist. Replace with "validate Orchestrator lists all 9 agents."

🎯 Phase 3 Runbook — Copy-Paste Ready
Step 1 — Boot everything with agents profile:

powershell
docker compose -f docker-compose.yml -f docker-compose.demo.yml --profile agents up -d --no-build
Step 2 — Confirm all 9 agents registered:

powershell
curl http://127.0.0.1:8081/agents
✅ Should return the 9 agents from config

Step 3 — Check Healer (correct port!):

powershell
curl http://127.0.0.1:8010/health
Step 4 — Seed the DB:

powershell
docker exec hypercode-core python seed_data.py
Step 5 — Fire a smoke task through Orchestrator:

powershell
curl -X POST http://127.0.0.1:8081/execute `
  -H "Content-Type: application/json" `
  -d '{"task": "hello mission", "description": "Return a one-line status message", "agent_type": "project_strategist"}'
Step 6 — Verify task completed:

powershell
curl http://127.0.0.1:8081/tasks
📋 Phase 3 "DONE" Contract
Check	Command	Pass =
All agents up	docker compose ps	9 agents Up
Orchestrator healthy	curl :8081/health	200 OK
Agents registered	curl :8081/agents	9 entries
Healer alive	curl :8010/health	200 OK
DB seeded	curl :8000/health	200 OK
Smoke task done	curl :8081/tasks	1+ completed task
⚡ Agent Utilization Right Now
🧠 System Architect → defines Phase 3 contract (above)

🔒 Security Engineer → reviews Docker socket permissions

🛠️ DevOps Engineer → fixes compose + socket mount

🩺 Healer Agent → validates self-restart on a forced-down agent

✅ QA Engineer → runs the 6-step runbook above and reports

📝 Tips & Tricks Writer → updates Phase Map doc to match reality

🎯 Next Win: Run Step 1 + 2 above right now and paste back what curl :8081/agents returns — we'll confirm exactly which agents woke up vs need a nudge!

🔥 BROski Power Level: System Architect
