from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, projects, tasks, dashboard, memory, orchestrator, broski, planning, hypersync, agent_keys, ops_dlq
from app.api.v1.endpoints import health
from app.ws import metrics_broadcaster, agents_broadcaster, events_broadcaster, logs_broadcaster
from app.routes import reliability, tasks as public_tasks

# Phase 2/3/4 endpoints require models added after the base image — import gracefully
try:
    from app.api.v1.endpoints import economy, access, graduate
    _HAS_PHASE234 = True
except Exception as _e:
    import logging as _log
    _log.getLogger(__name__).warning("Phase 2/3/4 endpoints unavailable (old image): %s", _e)
    _HAS_PHASE234 = False

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(memory.router, prefix="/memory", tags=["memory"])
api_router.include_router(orchestrator.router, prefix="/orchestrator", tags=["orchestrator"])
api_router.include_router(broski.router, prefix="/broski", tags=["broski"])  # 🔥 BROski$ Token System
api_router.include_router(planning.router, prefix="/planning", tags=["planning"])  # 🗺️ Planning System
api_router.include_router(hypersync.router, prefix="/hypersync", tags=["hypersync"])
api_router.include_router(agent_keys.router, prefix="", tags=["agent-keys"])  # 🔑 Phase 10D
api_router.include_router(ops_dlq.router, prefix="/ops", tags=["ops"])
if _HAS_PHASE234:
    api_router.include_router(economy.router,  prefix="/economy",  tags=["economy"])   # Phase 2: Token Sync
    api_router.include_router(access.router,   prefix="/access",   tags=["access"])    # Phase 3: Shop Bridge
    api_router.include_router(graduate.router, prefix="/graduate", tags=["graduate"])  # Phase 4: npm run graduate 🔥
api_router.include_router(health.router,   prefix="",           tags=["health"])      # Phase 5: Observability

# Dashboard live data — Task 2: GET /api/v1/metrics + WS /api/v1/ws/metrics
api_router.include_router(metrics_broadcaster.router, prefix="", tags=["metrics"])

# Dashboard live data — Task 3: GET /api/v1/agents/status + WS /api/v1/ws/agents
api_router.include_router(agents_broadcaster.router, prefix="", tags=["agents-status"])

# Dashboard live data — Task 5: GET /api/v1/events SSE + WS /api/v1/ws/events
api_router.include_router(events_broadcaster.router, prefix="", tags=["events"])

# Dashboard live data — Task 6: GET /api/v1/logs (no auth) + WS /api/v1/ws/logs
# Must be registered BEFORE dashboard compat so the public route wins on /logs
api_router.include_router(logs_broadcaster.router, prefix="", tags=["logs"])

# Dashboard compat — /execute endpoint; /logs here is shadowed by logs_broadcaster above
api_router.include_router(dashboard.router, prefix="", tags=["dashboard_compat"])

# Dashboard live data — Tasks 7 & 8: GET /api/v1/error-budget + GET /api/v1/system/state
api_router.include_router(reliability.router, prefix="", tags=["reliability"])

# Dashboard live data — Task 9: public task CRUD at /api/v1/tasks (no auth) + auto-task
api_router.include_router(public_tasks.router, prefix="", tags=["dashboard-tasks"])
