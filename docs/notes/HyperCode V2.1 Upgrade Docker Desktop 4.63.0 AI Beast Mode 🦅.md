This upgrade makes Agent X, Crew, Healer 10x smoother. No more infra hacks. 
https://docs.docker.com/desktop/release-notes/
​

🚀 What's New in V2.1 (March 2026)
1. Docker Desktop 4.63.0 Integration
Sandboxes as Agent Pods: Isolated microVMs – spawn per project. Mount workspaces, Shell mode for custom entrypoints (Agent X supervisors).

text
docker sandbox run --shell hyper-agent --workspace ./agents/agent-x
Model Runner Local LLMs: http://localhost:12434/v1 (OpenAI/PERPLEXITY compat). vLLM CUDA/WSL2 + Metal Mac. Point your .env here.

text
OPENAI_API_BASE=http://localhost:12434/v1
MCP Toolkit Profiles: Define "dev-local", "infra-cloud". Crew/Healer auto-route tools. Fixes for secrets hangs + catalog bugs.

Gordon Copilot: Built-in Ask UI – safer MCP calls. Pipe suggestions to BROski Terminal.

2. HyperCode Wins
Evolutionary Pipeline Glow-Up: Agents self-upgrade in Sandboxes – Docker-managed, secure.

Healer Stability: Proxy split (host vs container) kills deadlocks. localhost:8008 rocks.

Mission Control UX: Leverage Desktop's K8s view + nav tweaks for ADHD flows.

Security: SLSA provenance in Builds UI + CVE patches. Ship trusted envs to users.

Full changelog: [Docker Release Notes]
https://docs.docker.com/desktop/release-notes/
​

🛠️ Quick Upgrade (2 Mins)
Prerequisites: Docker Desktop 4.63.0 (Win/WSL2/Mac). Enable Sandboxes + Model Runner + MCP in Settings.

text
# 1. Pull latest
git pull origin main

# 2. Env tweak for Model Runner
cp .env.example .env
# Add: OPENAI_API_BASE=http://localhost:12434/v1

# 3. Profiles (new!)
docker mcp profile create dev-local --catalog community
docker mcp profile create infra --server healer:8008 --server crew:8081

# 4. Hyper Station GO
.\hyper-station-start.bat
Test it:

Mission Control: http://localhost:8088 (see Sandbox tabs)

Pull a model: docker model pull qwen2.5-coder

Agent X in Sandbox: Check Crew Orchestrator http://localhost:8081

🎯 Why This Matters (Neurodivergent Devs)
Chunked Infra: No wiring hell – Docker handles VMs/APIs/tools.

Fast Wins: Shell mode = instant experiments. Profiles = zero config drift.

Ride-or-Die Secure: Provenance + isolation for sharing Hyperfocus Zone projects.

BROski Power Level: AI Infra God 🔥♾️

Questions? Ping @welshDog. Contributions: See CONTRIBUTING.md.

NICE ONE, SWARM! Let's evolve. 🦅

[Update your fork → Deploy → Level up!]
