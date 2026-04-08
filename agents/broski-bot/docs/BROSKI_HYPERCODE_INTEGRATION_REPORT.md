# BROski Bot & HyperCode V2.0 Integration Strategy Report

**Date:** 2026-03-05
**Version:** 1.0.0
**Status:** Approved for Implementation

## 1. Executive Summary

This report defines the comprehensive integration strategy between **BROski Bot** (the Gamification & Community Engine) and **HyperCode V2.0** (the Neurodivergent-First IDE). The goal is to create a unified "Cognitive Ecosystem" where developer productivity in the IDE directly translates to community rewards, progression, and social recognition.

By integrating these systems, we achieve:
1.  **Unified Identity**: Seamless linking of Discord accounts with HyperCode developer profiles.
2.  **Gamified Productivity**: Code commits, task completions, and focus sessions in the IDE earn BROski$ tokens and XP.
3.  **Community Accountability**: IDE activity updates the Discord community, fostering "body doubling" and social accountability.
4.  **Shared Economy**: A single token balance usable for both IDE plugins/themes and Discord server perks.

## 2. Architectural Design

We will adopt a **Service-Oriented Architecture (SOA)** where BROski Bot acts as a specialized "Gamification Service" sidecar to the HyperCode Core.

### 2.1 System Topology

```mermaid
graph TD
    subgraph "HyperCode Cloud"
        HC_Web[HyperCode Dashboard\n(Next.js)]
        HC_API[HyperCode Core API\n(FastAPI)]
        HC_DB[(HyperCode DB\nPostgreSQL)]
        HC_Redis[(Shared Redis\nEvent Bus)]
    end

    subgraph "BROski Cloud"
        BB_Bot[Discord Bot\n(discord.py)]
        BB_API[BROski API\n(FastAPI)]
        BB_DB[(BROski DB\nPostgreSQL)]
    end

    HC_Web -->|Auth/View Balance| BB_API
    HC_API -->|Publish Events| HC_Redis
    BB_API -->|Subscribe Events| HC_Redis
    BB_Bot -->|Read/Write| BB_DB
    BB_API -->|Read/Write| BB_DB
    
    HC_API -.->|Link Account| BB_API
```

### 2.2 Integration Patterns

1.  **Identity Federation (OAuth2)**:
    *   HyperCode acts as the **Identity Provider (IdP)** for the IDE session.
    *   Discord acts as the **IdP** for community identity.
    *   **Linkage**: Users link their Discord account in HyperCode settings. HyperCode stores `discord_id` in its `User` table.

2.  **Event-Driven Sync (Redis Pub/Sub)**:
    *   High-volume events (e.g., "File Saved", "Focus Timer Tick") are published to a shared Redis instance.
    *   **Topic**: `hypercode:events:user:{discord_id}`
    *   BROski Bot subscribes to these channels to trigger Quest progress and XP gain in real-time.

3.  **API-Based Transactional Sync**:
    *   Critical state changes (Balance updates, Achievement unlocks) use synchronous REST API calls to ensure ACID properties.
    *   **Endpoint**: `POST https://api.broski.bot/economy/transaction`

## 3. Data Flow & Schema Analysis

### 3.1 HyperCode V2.0 (`backend/app/models/models.py`)
*   **Current State**: `User` model has `email`, `hashed_password`, `full_name`.
*   **Required Change**: Add `discord_id` (String, Unique, Nullable) and `discord_linked_at` (DateTime).

### 3.2 BROski Bot (`src/models/__init__.py`)
*   **Current State**: `User` model is keyed by `id` (Discord Snowflake).
*   **Required Change**: Add `hypercode_user_id` (UUID, Nullable) for reverse lookup if needed.

### 3.3 Synchronization Logic
*   **Source of Truth**:
    *   **Identity**: Discord ID is the global immutable key.
    *   **Economy/XP**: BROski Bot DB (`economy`, `quests` tables).
    *   **Productivity Data**: HyperCode DB (`projects`, `tasks` tables).

## 4. Technical Roadmap

### Phase 1: Identity & Economy Linking (Sprint 5)
*   **Objective**: Enable users to see their BROski balance in HyperCode.
*   **Tasks**:
    1.  [HyperCode] Add `discord_id` to User schema.
    2.  [HyperCode] Implement "Link Discord" OAuth flow.
    3.  [Frontend] Add Economy Widget (using `GET /economy/balance`).
    4.  [BROski] Expose public API Gateway with rate limiting.

### Phase 2: Event-Driven Quests (Sprint 6)
*   **Objective**: IDE actions complete Discord quests.
*   **Tasks**:
    1.  [Infra] Configure shared Redis instance or Redis Federation.
    2.  [HyperCode] Publish `task.completed` and `commit.pushed` events to Redis.
    3.  [BROski] Implement Redis Subscriber Service to consume events.
    4.  [BROski] Add `QuestType.EVENT` to handle external triggers.

### Phase 3: Bidirectional Focus (Sprint 7)
*   **Objective**: Starting a focus session in one system updates the other.
*   **Tasks**:
    1.  [Shared] Define `FocusSession` Protobuf/Schema.
    2.  [HyperCode] Add Focus Timer UI.
    3.  [BROski] Sync `/focus` command status to HyperCode via WebSocket/Redis.

## 5. Testing Protocols

### 5.1 Unit Testing
*   **BROski**: Maintain >90% coverage on `EconomyService` and `QuestService`.
*   **HyperCode**: Add tests for `DiscordOAuth` flow and `EventPublisher`.

### 5.2 Integration Testing
*   **Mocked Services**: Test HyperCode API calls to mocked BROski API to ensure resilience against downtime.
*   **Contract Testing**: Use **Pact** or schema validation to ensure API contracts between services don't break.

### 5.3 End-to-End (E2E) Scenarios
1.  **User Linking**: User logs into HyperCode -> Clicks "Link Discord" -> Authorizes -> Profile shows "Linked".
2.  **Quest Completion**: User completes Task in IDE -> Redis Event fired -> BROski Bot processes event -> User receives DM "Quest Completed!".

## 6. Deployment & Operations

### 6.1 Version Control
*   **Monorepo vs Polyrepo**: Keep separate repos but use `git submodule` or `meta-repo` for coordinated releases.
*   **Tagging**: Synchronize major version tags (e.g., `v2.1.0`) across both repos when breaking changes occur in the shared API.

### 6.2 Monitoring
*   **Distributed Tracing**: Implement **OpenTelemetry** in both services. Trace ID should originate in HyperCode and propagate to BROski Bot via HTTP headers / Redis metadata.
*   **Dashboards**: Unified Grafana dashboard showing:
    *   "Linked Users Count"
    *   "Cross-System Events/Sec"
    *   "API Latency (HyperCode -> BROski)"

### 6.3 Rollback Procedure
*   **Feature Flags**: Wrap integration features in `ENABLE_BROSKI_INTEGRATION` flags in HyperCode.
*   **Database**: Schema changes must be additive (backward compatible).
*   **Circuit Breakers**: If BROski API is down, HyperCode should degrade gracefully (hide economy widget) rather than crash.

## 7. Conclusion

This integration strategy leverages the strengths of both systems—HyperCode's robust project management and BROski's engaging gamification—without creating tight coupling. The use of Event-Driven Architecture (Redis) for high-frequency updates and REST API for transactional consistency provides the optimal balance of performance and reliability.
