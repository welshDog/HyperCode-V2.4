# 🧰 HyperCode V2.4 — Skills Index

WHY: This makes every Claude session “skill-aware” before touching Docker.

## ✅ Start Here (60 seconds)

1) Read [CLAUDE.md](file:///H:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4/CLAUDE.md)
2) Use local skills in `.claude/skills/` (auto-discovered)
3) Load external skills from `Hyperfocus-Global-Impact-Skills` when needed

## 🧠 Local Skills (this repo)

Path: `.claude/skills/<skill-name>/SKILL.md`

Good defaults:
- `docker-stack-ops` → safe compose ops + health checks
- `cve-trivy-scan` → keep 0 CRITICAL
- `hypercode-docker-ops` → HyperCode docker patterns
- `hypercode-agent-spawner` → spawner safety + limits
- `hypercode-security` → “don’t ship footguns”

## 🐳 External Skill Pack (Global Impact Skills)

Repo:
https://github.com/welshDog/Hyperfocus-Global-Impact-Skills

HyperDocker skills:
- `hyperdocker-image-optimizer/SKILL.md`
- `hyperdocker-compose-guardian/SKILL.md`
- `hyperdocker-healer-diagnostics/SKILL.md`

## 🧩 Best Starter Prompts (copy/paste)

### 🐳 Image Optimizer

Paste:
“Use HyperDocker Image Optimizer.
Refactor this Dockerfile into multi-stage.
Keep 0 secrets, add healthcheck, target 0 CRITICAL.”

### 🛡️ Compose Guardian

Paste:
“Use HyperDocker Compose Guardian.
Audit this compose for network isolation, memory limits, healthchecks.
Do not change docker-compose.yml without showing diff.”

### 🧯 Healer Diagnostics

Paste:
“Use HyperDocker Healer Diagnostics.
Assume a restart loop.
Give a calm step-by-step triage: ps → health → logs → metrics.”

## 🧨 Red Rules (always)

- 🔴 Never touch `.env` secrets
- 🔴 Never delete files without asking
- 🟡 Compose changes must keep `data-net` + `obs-net` internal

