🚀 HyperCode V2.0 — New User Setup Guide
🛠️ Before You Start — Prerequisites
Make sure you have these installed first:

Docker Desktop → docker.com/products/docker-desktop

Windows PowerShell (already on Windows — just search it in Start Menu)

Git → git-scm.com (to clone the repo)

API Keys for at least one AI provider (PERPLEXITY or OpenAI — or both!)

📦 Step 1 — Clone the Repo
Open PowerShell and run:
​

powershell
git clone https://github.com/welshDog/HyperCode-V2.0.git
cd HyperCode-V2.0
🔑 Step 2 — Set Up Your Environment File
This is the most important step — your .env file is the brain config.
​

1. Copy the example file:

powershell
Copy-Item .env.example .env
2. Open .env in a text editor (Notepad, VS Code, whatever you like):

powershell
notepad .env
3. Fill in these KEY values — leave the rest as default for now:

Variable	What to put	Where to get it
API_KEY	Any strong random string	Make one up, e.g. mySecretKey123!
HYPERCODE_JWT_SECRET	A long random string	Generate at randomkeygen.com
JWT_SECRET	Same or different random string	Same as above
HYPERCODE_MEMORY_KEY	Another random string	Same as above
PERPLEXITY_API_KEY	Starts with sk-ant-api03-...	console.PERPLEXITY.com
OPENAI_API_KEY	Starts with sk-proj-...	platform.openai.com
POSTGRES_PASSWORD	Change from changeme	Make it something secure!
GF_SECURITY_ADMIN_PASSWORD	Change from admin	Your choice
💡 You only NEED one of PERPLEXITY or OpenAI — but both is better!

⚡ Step 3 — Install Desktop Shortcuts (Recommended!)
Run this once — it puts one-click launch buttons on your Desktop:
​

powershell
.\scripts\install_shortcuts.ps1
This creates two shortcuts:

🟢 HYPER STATION START — fires up the whole system

🔴 HYPER STATION STOP — shuts it all down cleanly

🔥 Step 4 — LAUNCH IT!
Either double-click HYPER STATION START on your Desktop, OR run:
​

powershell
.\scripts\hyper-station-start.bat
Docker will pull all the containers and spin everything up. First launch takes a couple of minutes — after that it's fast ⚡

✅ Step 4.5 — Verify It’s Actually Ready (recommended)
Before you start clicking around, confirm the stack is healthy:

powershell
docker compose -f docker-compose.yml -f docker-compose.demo.yml ps

Then run quick health checks:

powershell
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8081/health
curl http://127.0.0.1:8010/health
curl http://127.0.0.1:9090/-/ready

Expected:
- HTTP 200 responses
- crew-orchestrator `/metrics` works once Phase 4 is enabled:

powershell
curl http://127.0.0.1:8081/metrics | Select-String "smoke_request_total"

🌐 Step 5 — Open Your Interfaces
Once it's running, open your browser and go to these:
​

Interface	URL	What it does
🚀 Mission Control	http://localhost:8088	Main dashboard — start here
🖥️ BROski Terminal	http://localhost:3000	CLI command interface
🧠 Crew Orchestrator	http://localhost:8081	Manage your AI agents
❤️ Healer Agent	http://localhost:8010	System health monitor (container listens on 8008)
📝 Core API Docs	http://localhost:8000/docs	API reference
📊 Grafana	http://localhost:3001	Observability & metrics
🧠 Optional — Local LLM with Ollama
Want to run AI completely offline for free? Install Ollama!
​

powershell
# After installing Ollama from ollama.com:
ollama pull tinyllama
Your .env is already pre-configured for Ollama at http://localhost:11434 — it just works 🎉

🆘 Something Not Working?
Check these docs in the repo:

docs/TROUBLESHOOTING.md — common fixes

docs/DEPLOYMENT.md — Docker setup deep dive

Quick fixes (common first-run issues):

Problem	What to do
Docker isn’t starting	Open Docker Desktop and wait until it says “Running”
Ports already in use (8088/8081/8000/3001)	Close the conflicting app or change ports in docker-compose.yml
Containers restarting	Check logs: `docker logs <service-name> --tail 200`
Core API unhealthy	Check `.env` values (POSTGRES_PASSWORD, API keys) and `docker logs hypercode-core`
Healer unhealthy	Check `docker logs healer-agent` and confirm Docker socket mount is present
No Grafana data	Confirm Prometheus is up (http://localhost:9090) and targets are `UP`

🎯 Next Win: Open http://localhost:8088 and explore Mission Control — that's your home base!

🚀 HyperCode V2.0 — Quick Cheat Sheet
text
1️⃣  Install:  Docker Desktop + Git
2️⃣  Clone:   git clone github.com/welshDog/HyperCode-V2.0.git
3️⃣  Config:  cp .env.example .env → fill in your API keys
4️⃣  Setup:   .\scripts\install_shortcuts.ps1
5️⃣  Launch:  Double-click HYPER STATION START 🟢
6️⃣  Open:    http://localhost:8088 → Mission Control 🎯
7️⃣  Explore:  http://localhost:3000 → BROski Terminal
8️⃣  Agents:  http://localhost:8081 → Crew Orchestrator
9️⃣  Health:  http://localhost:8010 → Healer Agent
🔟  API:     http://localhost:8000/docs → Core API Docs
🔡  Metrics: http://localhost:3001 → Grafana
🔢  Optional: http://localhost:11434 → Local LLM with Ollama
🔣  Stop:    Double-click HYPER STATION STOP 🔴


🔥 Bonus Find
Spotted your THE-HYPERCODE repo too — the neurodivergent programming language with quantum + molecular computing is live and has its first release (v0.1.0)! That's a whole other beast we can document the same way if you want.
