# NemoClaw Over-Execution Deep Dive (2026-03-19)

## Scope

This report analyzes repeated NemoClaw execution runs observed in:

- `logs/nemoclaw/` (all `.log` files)
- `scripts/nemoclaw/` (installation/onboarding/validation helpers)
- `agents/` (to confirm whether any running agent is triggering NemoClaw repeatedly)
- `docs/integrations/nemoclaw.md` (operational guidance alignment)

“Over-execution” here means repeated onboarding attempts and/or noisy unhealthy OpenShell cluster behavior that causes unnecessary work, long build retries, and resource churn.

## Executive Summary

The repeated runs are not caused by an infinite loop in HyperCode agents. The primary driver is repeated onboarding attempts after failures caused by Docker Desktop / WSL integration instability and Docker build pipeline failures (containerd/buildkit stream issues and one npm failure during image build). A secondary amplifier is a noisy OpenShell cluster health state that times out frequently, generating repeated healthchecks and contributing to perceived instability.

Mitigations were implemented to prevent runaway reruns (lock + rate limit + skip onboarding if sandbox already exists) and to provide diagnostics tooling for fast classification and remediation.

## Evidence (Log-Based Findings)

### 1) Docker not reachable from WSL (preflight failure)

Multiple runs terminate immediately with:

- “Docker is not running. Please start Docker and try again.”

Examples:

- [onboard-20260318T082417Z.log](file:///H:/HyperStation%20zone/HyperCode/HyperCode-V2.0/logs/nemoclaw/onboard-20260318T082417Z.log#L1-L7)
- [onboard-20260319T125749Z.log](file:///H:/HyperStation%20zone/HyperCode/HyperCode-V2.0/logs/nemoclaw/onboard-20260319T125749Z.log#L1-L7)

Impact:

- Each failure typically triggers a retry, increasing “run count” without progress.

### 2) Docker build stream failures during sandbox image creation (high-cost failures)

Several runs reach sandbox creation and fail inside Docker image build, which is expensive (minutes of build time per attempt).

Observed failure modes:

- containerd/overlay lease/mount errors:
  - [onboard-20260318T082722Z.log](file:///H:/HyperStation%20zone/HyperCode/HyperCode-V2.0/logs/nemoclaw/onboard-20260318T082722Z.log#L126-L135)
- generic stream transport failure:
  - [onboard-20260318T103633Z.log](file:///H:/HyperStation%20zone/HyperCode/HyperCode-V2.0/logs/nemoclaw/onboard-20260318T103633Z.log#L64-L69)

Impact:

- Sandbox creation restarts from scratch on the next attempt, repeating long `npm install` and base image steps.

### 3) npm failure inside sandbox image build (rare, but blocks progress)

One run failed during `npm install -g openclaw@...` with:

- “npm error Exit handler never called!”

Example:

- [onboard-20260319T113734Z.log](file:///H:/HyperStation%20zone/HyperCode/HyperCode-V2.0/logs/nemoclaw/onboard-20260319T113734Z.log#L71-L89)

Impact:

- Causes immediate build failure and another retry loop.

### 4) OpenShell cluster health flapping / timeouts (execution amplifier)

The local OpenShell cluster container (`openshell-cluster-nemoclaw`) frequently reports healthcheck timeouts. This does not always mean the cluster is unusable, but it increases noise and can correlate with slow/unreliable sandbox provisioning.

Impact:

- Adds persistent background “activity” via repeated healthchecks.
- Encourages repeated manual retries even when the underlying issue is Docker/build stability rather than NemoClaw logic.

## Agent Folder Audit (HyperCode Runtime)

Repo-wide search shows no `nemoclaw`, `openshell`, or `openclaw` invocations inside `agents/` or `backend/`. Direct NemoClaw execution is confined to `scripts/nemoclaw/` wrappers.

Operationally relevant background loops were reviewed:

- Crew orchestrator agent health polling: sleeps 30s between cycles and uses HTTP timeouts ([crew-orchestrator/main.py](file:///H:/HyperStation%20zone/HyperCode/HyperCode-V2.0/agents/crew-orchestrator/main.py#L51-L112)).
- Healer watchdog loop: sleeps at least 5s (default 60s) and has a circuit breaker to avoid runaway restarts ([healer/main.py](file:///H:/HyperStation%20zone/HyperCode/HyperCode-V2.0/agents/healer/main.py#L304-L313)).

Conclusion:

- There is no evidence of an infinite loop in agents causing NemoClaw over-execution.
- Indirectly, heavy system load from many containers can increase the probability of Docker Desktop buildkit/containerd failures, but the trigger for NemoClaw reruns is manual/script re-invocation after failures.

## Root Cause Analysis

Primary root causes:

1) Intermittent Docker Desktop ↔ WSL Docker daemon reachability during onboarding attempts.
2) Docker Desktop build pipeline instability during the OpenShell sandbox image build (containerd mount/lease errors and stream transport failures).

Secondary contributing causes:

1) OpenShell cluster healthcheck timeouts (noise + perceived instability).
2) One npm failure during image build (rare, but blocks progress when it happens).

## Implemented Fixes (Prevention + Operability)

### A) Prevent runaway reruns (lock + rate limit + skip onboarding if already onboarded)

Updated: [onboard.sh](file:///H:/HyperStation%20zone/HyperCode/HyperCode-V2.0/scripts/nemoclaw/onboard.sh)

Changes:

- Uses a lock directory to prevent concurrent runs.
- Records run timestamps and refuses execution if more than 3 onboarding attempts occur within 1 hour.
- Checks whether the target sandbox already exists (`nemoclaw list`) and exits successfully if it does.
- Performs a Docker reachability check (with retries) before onboarding.
- Runs onboarding interactively and logs via `script` when available.

### B) Add diagnostics tooling (fast classification)

Added:

- [diagnose.sh](file:///H:/HyperStation%20zone/HyperCode/HyperCode-V2.0/scripts/nemoclaw/diagnose.sh)
- [diagnose.ps1](file:///H:/HyperStation%20zone/HyperCode/HyperCode-V2.0/scripts/nemoclaw/diagnose.ps1)

Capabilities:

- Summarizes the most common failure signatures across all NemoClaw logs.
- Verifies Docker reachability and `nemoclaw` availability.
- Reports OpenShell cluster container presence/status.

### C) Reduce OpenShell healthcheck churn (optional tuning)

Added:

- [tune-openshell-health.sh](file:///H:/HyperStation%20zone/HyperCode/HyperCode-V2.0/scripts/nemoclaw/tune-openshell-health.sh)
- [tune-openshell-health.ps1](file:///H:/HyperStation%20zone/HyperCode/HyperCode-V2.0/scripts/nemoclaw/tune-openshell-health.ps1)

Effect:

- Increases healthcheck timeout/interval to reduce timeouts and thrash on slower hosts.

## Recommendations (Optimization)

### System stability (highest ROI)

- Ensure Docker Desktop is running and WSL integration is enabled for the Ubuntu distro used for NemoClaw.
- Avoid WSL shutdown/restarts during onboarding.
- If “Docker build stream error” appears, restart Docker Desktop (resets containerd/buildkit) before retrying.
- If disk is tight, prune old images/build cache before retrying; containerd mount/lease errors are more common under pressure.

### Process control (prevents over-execution)

- Use `scripts/nemoclaw/onboard.sh` (now guarded) instead of ad-hoc reruns.
- Run `scripts/nemoclaw/diagnose.sh` after the first failure and follow the top recommendation instead of retrying repeatedly.

### Documentation alignment

Updated: [nemoclaw.md](file:///H:/HyperStation%20zone/HyperCode/HyperCode-V2.0/docs/integrations/nemoclaw.md)

- Added diagnostics commands and clarified how `NVIDIA_API_KEY` is sourced locally without committing secrets.

## Next Steps

If onboarding is still required:

1) Run `scripts/nemoclaw/diagnose.ps1` and resolve the top listed issue (usually Docker reachability or build pipeline stability).
2) Run a single onboarding attempt via `scripts/nemoclaw/onboard.ps1` and avoid parallel attempts.
3) If OpenShell stays noisy/unhealthy, run `scripts/nemoclaw/tune-openshell-health.ps1` to reduce healthcheck churn.

