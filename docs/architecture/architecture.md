# HyperCode Agent Crew - Architecture

## System Overview

```mermaid
graph TD
    User[Client Applications] -->|HTTP/WS| API[Crew Orchestrator]
    Dashboard[HyperFlow Dashboard] -->|HTTP/WS| Core[HyperCode Core]
    API -->|Delegation| Strat[Project Strategist]
    API -->|Coordination| Arch[System Architect]
    
    subgraph "Data Layer"
        Redis[(Redis Cache & Queue)]
        DB[(PostgreSQL History)]
        MinIO[(Object Storage)]
    end
    
    subgraph "Specialist Swarm (Tier 2)"
        FE[Frontend Specialist]
        BE[Backend Specialist]
        QA[QA Engineer]
        DevOps[DevOps Engineer]
        Sec[Security Engineer]
    end
    
    subgraph "Observability"
        Prom[Prometheus]
        Graf[Grafana]
        Jaeger[Jaeger Tracing]
        Tempo[Tempo]
        Loki[Loki]
    end

    subgraph "AI Inference"
        Ollama[Ollama (Local LLM)]
        PERPLEXITY[PERPLEXITY API]
    end

    Strat -->|Task| Redis
    Arch -->|Standards| Redis
    Redis -->|Pub/Sub| Specialist Swarm
    Specialist Swarm -->|Results| Redis
    Redis -->|Aggregation| API
    
    Core -->|Logs| Loki
    Core -->|Metrics| Prom
    Prom --> Graf
    
    Dashboard -->|Viz| Core
    Specialist Swarm -->|Context| Ollama
```

## Agent Hierarchy

### Tier 1: Strategic Agents (Orchestrators)
- **Project Strategist**: Plans, breaks down tasks, delegates
- **System Architect**: Defines architecture, patterns, standards
- **Crew Orchestrator**: Coordinates the entire swarm

**Model**: Claude Opus (highest reasoning capability)
**Responsibilities**: High-level planning, decision-making

### Tier 2: Specialist Agents (Executors)
- **Frontend Specialist**: UI/UX, React, Next.js
- **Backend Specialist**: APIs, business logic, Python
- **Database Architect**: Schema, queries, optimization
- **QA Engineer**: Testing, validation, quality assurance
- **DevOps Engineer**: CI/CD, Docker, Kubernetes
- **Security Engineer**: Security audits, vulnerability scanning
- **Healer Agent**: Self-healing monitoring & recovery
- **Pulse Agent (CLI)**: Infrastructure health checks
- **Archivist (CLI)**: Technical research & documentation

**Model**: Claude Sonnet (fast, efficient) / Local Models via Ollama
**Responsibilities**: Specialized task execution

## Communication Flow

### 1. Task Submission
```
User → Dashboard/CLI → Orchestrator → Project Strategist → Breakdown → Specialists
```

### 2. Inter-Agent Communication
```
Agent A → Redis Pub/Sub → Agent B
         ↓
    PostgreSQL (persistence)
```

### 3. Result Aggregation
```
Specialists → Results → Orchestrator → Client/Dashboard
                ↓
           Task History (PostgreSQL)
```

## Data Flow

### Task Planning
1. User submits task to Orchestrator (via CLI or Dashboard)
2. Orchestrator forwards to Project Strategist
3. Strategist analyzes and creates subtasks
4. Subtasks stored in Redis with status
5. Specialists notified via Redis pub/sub

### Task Execution
1. Specialist receives task from queue
2. Loads Hive Mind context (standards, skills)
3. Calls AI Model (Claude/Ollama) with enriched prompt
4. Stores result in Redis
5. Notifies Orchestrator of completion

### Result Collection
1. Orchestrator monitors Redis for completions
2. Aggregates specialist results
