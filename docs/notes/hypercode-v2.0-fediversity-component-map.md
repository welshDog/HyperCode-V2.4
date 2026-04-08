# HyperCode V2.0 – Fediversity Component Mapping

**Document Version:** 1.1
**Date:** 2026-03-06
**Repository:** [welshDog/HyperCode-V2.0](https://github.com/welshDog/HyperCode-V2.0)
**License:** AGPL-3.0 (GPL-compatible, copyleft-enforced)
**Maintainer:** Lyndz Williams (Wales, EU/EEA)

---

## Overview

HyperCode V2.0 is a **neurodivergent-first, open-source AI development environment** built on a fully containerized, self-hostable stack. Every component listed below is designed to:

- **Empower users over platforms:** Run locally, no vendor lock-in, no cloud dependency.
- **Reduce cognitive overload:** Visual, chunked, accessible interfaces built for ADHD, autism, and dyslexia.
- **Strengthen the open internet:** All code is AGPL-licensed, all protocols are open, all data stays under user control.

This document maps HyperCode's runnable components to **NGI Fediversity themes** (decentralisation, federation, privacy, interoperability, EU sovereignty) and demonstrates compliance with **NLnet eligibility criteria** (open-source, WCAG accessibility, public documentation).

---

## Component Catalogue

### 1. Infrastructure Services

#### **Redis**
- **Official Name in Repo:** `redis`
- **Technology Stack:** Redis 7 (Alpine Linux base image)
- **Primary Function:** In-memory key-value store for agent state, session caching, and Celery task queuing.
- **Default Port/Endpoint:** `6379` (internal), exposed to backend-net and data-net
- **Fediversity Relevance:**
  - **Decentralisation:** Self-hosted data layer; no external cloud services.
  - **Privacy:** All session/state data remains on-premises.
  - **Interoperability:** Standard Redis protocol.
- **EU Audit Compliance:**
  - **Resource Efficiency:** Configured with LRU eviction and 512MB hard cap to prevent resource exhaustion.

#### **PostgreSQL**
- **Official Name in Repo:** `postgres`
- **Technology Stack:** PostgreSQL 15 (Alpine Linux base image)
- **Primary Function:** Relational database for agent memory, user settings, project metadata, and audit logs.
- **Default Port/Endpoint:** `5432` (internal)
- **Fediversity Relevance:**
  - **Decentralisation:** Self-hosted SQL database.
  - **Privacy:** Sensitive data stored locally with GDPR-compliant schemas.
  - **Open Standards:** Fully SQL-standard compliant.

#### **MinIO**
- **Official Name in Repo:** `minio`
- **Technology Stack:** MinIO (S3-compatible object storage)
- **Primary Function:** Stores code snapshots, agent outputs, user uploads.
- **Default Port/Endpoint:** `9000` (API), `9001` (Console)
- **Fediversity Relevance:**
  - **Decentralisation:** Self-hosted S3 replacement.
  - **Interoperability:** S3 API compatibility enables migration (no lock-in).
  - **Data Sovereignty:** Data stays in EU; no cross-border data transfer.

#### **ChromaDB**
- **Official Name in Repo:** `chroma`
- **Technology Stack:** ChromaDB (Vector Database)
- **Primary Function:** Semantic embeddings for RAG (Retrieval-Augmented Generation).
- **Default Port/Endpoint:** `8009` (mapped from 8000)
- **Fediversity Relevance:**
  - **Privacy:** User code embeddings never leave the local network.
  - **Interoperability:** REST API compatible with various embedding models.

#### **HyperCode Core**
- **Official Name in Repo:** `hypercode-core`
- **Technology Stack:** FastAPI (Python 3.11), Prisma, Celery
- **Primary Function:** Central API orchestrating agents and context.
- **Default Port/Endpoint:** `8000`
- **Fediversity Relevance:**
  - **Decentralisation:** API-first design enables horizontal scaling.
  - **Open Standards:** OpenAPI docs at `/docs`.
- **EU Audit Compliance:**
  - **Security:** `no-new-privileges:true` security context applied.

---

### 2. AI Agents Layer (The "Swarm")

This layer implements the **federated intelligence** architecture. Each agent is an independent microservice that communicates via standard HTTP/Redis protocols, ensuring modularity and replaceability.

#### **Crew Orchestrator**
- **Official Name in Repo:** `crew-orchestrator`
- **Technology Stack:** Python 3.11, FastAPI
- **Primary Function:** Lifecycle management of all other agents; assigns tasks and monitors health.
- **Default Port/Endpoint:** `8081` (External), `8080` (Internal)
- **Fediversity Relevance:**
  - **Federation:** Can coordinate agents running on different nodes/containers.
  - **Resilience:** Decouples task submission from execution.

#### **Project Strategist**
- **Official Name in Repo:** `project-strategist`
- **Technology Stack:** Python 3.11, LangChain
- **Primary Function:** High-level planning, breaking down complex user requests into sub-tasks.
- **Default Port/Endpoint:** `8001`
- **Fediversity Relevance:**
  - **Accessibility:** Translates vague natural language into technical specifications, aiding neurodivergent users.

#### **Healer Agent**
- **Official Name in Repo:** `healer-agent`
- **Technology Stack:** Python 3.11, Docker SDK
- **Primary Function:** Self-healing system; monitors container health and restarts failed services automatically.
- **Default Port/Endpoint:** `8010`
- **Fediversity Relevance:**
  - **Sustainability:** Reduces need for manual maintenance; keeps system running efficiently.
  - **Reliability:** Implements circuit breaker patterns to prevent cascading failures.

#### **Specialist Agents**
- **Components:**
  - `frontend-specialist` (Port 8002): UI/UX generation.
  - `backend-specialist` (Port 8003): API logic.
  - `database-architect` (Port 8004): Schema design.
  - `qa-engineer` (Port 8005): Testing and validation.
  - `devops-engineer` (Port 8006): CI/CD pipelines.
  - `security-engineer` (Port 8007): Vulnerability scanning.
  - `system-architect` (Port 8008): System design.
- **Fediversity Relevance:**
  - **Modularity:** Users can enable/disable specific specialists based on resource availability.
  - **Interoperability:** All agents share a common communication protocol (HyperCode Agent Protocol).

---

### 3. Frontend Layer (User Interface)

#### **Mission Control (Dashboard)**
- **Official Name in Repo:** `hypercode-dashboard`
- **Technology Stack:** Next.js 14, React, Tailwind CSS
- **Primary Function:** Visual interface for managing projects, viewing agent activities, and system health.
- **Default Port/Endpoint:** `8088`
- **Fediversity Relevance:**
  - **Accessibility:** WCAG 2.2 AAA targeted design (high contrast, screen reader support).
  - **User Control:** Provides transparency into AI actions; "Undo" capability for all agent operations.
- **EU Audit Compliance:**
  - **Privacy UI:** Dedicated settings for data retention and telemetry opt-out (default: off).

---

### 4. Observability & Monitoring Layer

Provides transparency and auditability required for EU-funded open source projects.

#### **Prometheus & Grafana**
- **Components:** `prometheus` (9090), `grafana` (3001)
- **Primary Function:** Metric collection and visualization.
- **Fediversity Relevance:**
  - **Transparency:** Users can see exactly what resources are being used.
  - **Performance:** Helps optimize energy consumption (Green IT).

#### **Logging Stack (Loki/Promtail/Tempo)**
- **Components:** `loki` (3100), `promtail`, `tempo` (3200)
- **Primary Function:** Centralized logging and distributed tracing.
- **Fediversity Relevance:**
  - **Auditability:** Full trace logs of every AI decision and action for accountability.

---

## Security & Compliance Specification (EU Audit)

1.  **Container Security:**
    - All containers run with `security_opt: - no-new-privileges:true`.
    - Non-root users used where possible (e.g., `appuser` in Core).
    - Read-only volume mounts (`:ro`) for configuration and shared knowledge.

2.  **Network Isolation:**
    - **`backend-net`**: Restricted internal network for agent-to-agent communication.
    - **`data-net`**: Isolated network for storage (Redis, MinIO, Postgres).
    - **`frontend-net`**: Public-facing network (Dashboard).

3.  **Data Sovereignty:**
    - 100% On-Premise. No "phone home" telemetry by default.
    - All external AI calls (PERPLEXITY/OpenAI) are proxied through Core, allowing for easy swapping to local LLMs (Ollama) for full air-gap capability.

4.  **Licensing:**
    - Entire stack is AGPL-3.0 or compatible, ensuring any modifications remain open source.
