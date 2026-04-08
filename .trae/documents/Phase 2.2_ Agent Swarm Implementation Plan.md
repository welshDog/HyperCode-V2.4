# Implementation Plan: Phase 2.2 - The Agent Swarm

We will execute Phase 2.2 in two logical stages to ensure stability. This plan focuses on **Step 1: Agent Registry & Event Bus Hardening** and **Step 2: Architect Agent Scaffolding**.

## 1. Upgrade Agent Registry (in `hypercode-core`)
The current `hypercode-core` already has a basic Redis-based registry (`agent_registry.py`) and API (`agents.py`). We will upgrade this to meet the "Centralized Agent Registry" requirements without creating a separate microservice (unless strictly necessary, but leveraging the Core is more efficient for now).

- **Schema Update**:
    - Update `app/schemas/agent.py` to include: `version`, `health_url`, `topics`, `capabilities`.
    - Enforce immutability logic in `AgentRegistrationRequest`.
- **Service Upgrade (`app/services/agent_registry.py`)**:
    - Switch from purely Redis-based ephemeral storage to **PostgreSQL + Redis**.
    - Implement `register` (idempotent), `deregister`, `update`, `query`.
    - **Persistence**: Add `Agent` model to Prisma schema for long-term storage.
    - **Real-time Watch**: Implement SSE (Server-Sent Events) endpoint `/agents/watch` using Redis Pub/Sub to broadcast registry changes.
- **API Update (`app/routers/agents.py`)**:
    - Add `GET /watch` (SSE).
    - Ensure CRUD endpoints match the new service logic.

## 2. Harden Event Bus
- **File**: `app/services/event_bus.py`
- **Features**:
    - **Deduplication**: Use Redis Sets to track message UUIDs with a TTL.
    - **ACLs**: Implement `can_publish(agent_role, topic)` and `can_subscribe(agent_role, topic)` checks.
    - **Circuit Breaker**: Add logic to track failed health checks and block publishing if threshold > 3.

## 3. Scaffold Architect Agent
- **Directory**: `agents/architect` (New)
- **Tech Stack**: TypeScript / NestJS.
- **Action**:
    - Create `Dockerfile` and `docker-compose` entry.
    - Initialize a basic NestJS app structure (manually or via script).
    - Implement `main.ts` with:
        - Lifecycle hooks (`onModuleInit`, `onModuleDestroy`).
        - Event Bus connection (Redis).
        - Health check endpoint `/health`.
    - **Note**: Since I cannot run `nest new`, I will create the minimal file structure manually (`package.json`, `tsconfig.json`, `src/main.ts`, `src/app.module.ts`).

## 4. Verification
- **Test**: Update `tests/test_agents.py` to verify the new Registry features (persistence, SSE).
- **Run**: Spin up the Architect container (via `docker-compose up`) and verify it registers itself with the Core.

## Execution Steps
1.  **Registry**: Update Prisma schema -> Generate Client -> Update Pydantic Schemas -> Update Registry Service -> Update Router.
2.  **Event Bus**: Add ACLs and Deduplication logic.
3.  **Architect**: Create files in `agents/architect`, add to `docker-compose.yml`, build and start.
4.  **Validate**: Run integration tests.
