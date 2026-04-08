# Goal for the Agents

**Doc Tag:** v2.0.0 | **Last Updated:** 2026-03-10

You want a team that can:

- Use TinyLlama (model runner) as the safe default brain.
- Be packaged + versioned as a Docker agent config.
- Be shared via registry and used from editors / MCP clients.

## Local Model Defaults (Resource-safe)

Use TinyLlama as the default brain, but allow automatic fallback to the smallest available quantized model when TinyLlama is not present.

Recommended env defaults:

```text
DEFAULT_LLM_MODEL=auto
OLLAMA_MODEL_PREFERRED=tinyllama:latest,tinyllama,phi3:latest,phi3
OLLAMA_MAX_MODEL_SIZE_MB=2500
OLLAMA_TEMPERATURE=0.3
OLLAMA_TOP_P=0.9
OLLAMA_TOP_K=40
OLLAMA_REPEAT_PENALTY=1.1
OLLAMA_NUM_CTX=2048
OLLAMA_NUM_PREDICT=256
```

2. Minimal hyperfocus-team.yaml (agents + TinyLlama)
Example agent config you can adapt (high level, not exact schema):

text
version: v1
name: hyperfocus-team
description: >
  Hyperfocus Zone agents. Root planner + local TinyLlama summariser.

model_providers:
  - name: local-tinyllama
    type: mcp
    args:
      command: docker
      args:
        - "model"
        - "serve"
        - "mcp"
        - "tinyllama"   # your Model Runner model name

agents:
  - name: root_planner
    description: >
      Orchestrator. Decides which sub-agent to call.
    model:
      provider: local-tinyllama
    instructions: |
      You are the Hyperfocus Planner.
      - Break tasks into small, ADHD-friendly steps.
      - Delegate summarising or code reading to `notes_summariser`.
      - Keep responses short first, then offer deeper detail.
      - Prefer local TinyLlama; only ask for remote power if explicitly told.

  - name: notes_summariser
    description: >
      Uses TinyLlama to summarise logs, notes, git diffs.
    model:
      provider: local-tinyllama
    instructions: |
      You summarise text into:
      - Bullet list of key points
      - 3 next actions for BROski
      - Keep language casual and supportive.
      Always assume low cognitive load: no walls of text.

  - name: code_helper
    description: >
      Helps with code explanations using TinyLlama.
    model:
      provider: local-tinyllama
    instructions: |
      Explain code in small chunks.
      - First: one-sentence plain-English summary.
      - Then: numbered steps of what happens.
      - Then: 1–3 ideas to improve readability or structure.
This gives the agents explicit behaviour tuned to Hyperfocus and keeps everything on TinyLlama by default.
​

3. Instructions for the agents (behavioural rules)
Add something like this to your root agent instructions block:

“Always respond in two phases:

short ‘TL;DR’ answer (1–3 lines),

optional deeper explanation with headings and bullets.”

“Break work into micro‑tasks and propose the next single step, not a giant plan.”

“Use notes_summariser for any long text: logs, docs, chat histories.”

“If system resources are low, choose shorter outputs and smaller context windows.”

These instructions live directly in the YAML under instructions: so they travel with the agent when shared.

4. Sharing your agents via Docker registry
Once hyperfocus-team.yaml exists:

Log in to your registry:

bash
docker login
(or your custom registry auth).
​

Publish the agent config as an OCI artefact:

bash
docker agent push ./hyperfocus-team.yaml welshdog/hyperfocus-team
docker agent push ./hyperfocus-team.yaml welshdog/hyperfocus-team:v1.0.0
docker agent push ./hyperfocus-team.yaml welshdog/hyperfocus-team:latest
This creates the repo if it doesn’t exist.
​

Teammates (or future you) can then:

bash
docker agent pull welshdog/hyperfocus-team
docker agent run welshdog/hyperfocus-team
pull saves a local YAML, run executes directly from registry.
​

5. Using it from editor & MCP (upgrades / integrations)
You can plug this shared agent into:

Editor (ACP) config – always latest version of your crew:
​

json
{
  "agent_servers": {
    "hyperfocus": {
      "command": "docker",
      "args": ["agent", "serve", "acp", "welshdog/hyperfocus-team:latest"]
    }
  }
}
MCP client – expose it as a tool in any MCP‑aware app:
​

json
{
  "mcpServers": {
    "hyperfocus": {
      "command": "docker",
      "args": ["agent", "serve", "mcp", "welshdog/hyperfocus-team:latest"]
    }
  }
}
Whenever you push a new version tag (e.g. v1.1.0), clients that point at :latest automatically use the upgraded instructions/agents on next restart.
​

6. Extra Docker “upgrades” you can layer later
From the docs menus you’ve got a few more power‑ups to explore when ready:

RAG support: plug your own docs / notes into the agent via RAG endpoints.

Evals: define evals to regression‑test your agent behaviours across updates.

Sandboxes & Model Runner: isolate risky tool execution and host more local models.

MCP Catalog: bring in extra tools (filesystem, web, git) declaratively.
