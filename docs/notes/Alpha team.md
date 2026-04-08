# 🧠 Alpha Team — Routing Rules

Hunter Alpha is the meta-architect model for repo-wide planning, evolution design, and long multi-step missions.

Healer Alpha is the incident/recovery model behind Healer Agent v2 for incident response and multimodal debugging.

Privacy rule: do not send secrets, prod credentials, or sensitive customer data to either model. Provider prompts/completions may be logged.

## Source of Truth

- Model docs:
  - `docs/models/HUNTER_ALPHA.md`
  - `docs/models/HEALER_ALPHA.md`
- Backend routing implementation:
  - `backend/app/core/model_routes.py`
- Upgrade roadmap and status reporting:
  - `docs/plans/ALPHA_TEAM_UPGRADE_INITIATIVE.md`
  - `docs/reports/status/ALPHA_TEAM_STATUS_TEMPLATE.md`

## Routing Triggers (Summary)

Use **Hunter Alpha** when any of these are true:
- Task spans multiple subsystems
- Task kind is architecture/roadmap/system_design/evolution/planning
- Context estimate is very large (e.g., > 120k tokens)
- Cross-repo synthesis is required

Use **Healer Alpha** when any of these are true:
- Incident/recovery/triage/self-heal work
- Inputs include images/audio
- Multiple signals must be correlated (logs + metrics + traces + screenshots)
