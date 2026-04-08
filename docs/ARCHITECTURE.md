# HyperCode V2.0: Architecture & Technical Manual

## Executive Summary
HyperCode-V2.0 is an advanced **AI-powered software development ecosystem** designed to automate complex coding workflows through a "Swarm Intelligence" architecture. It replaces the traditional solo-developer model with a coordinated team of specialized AI agents (The Translator, The Medic, The Archivist) that collaborate to plan, execute, and monitor software projects. The system emphasizes **"Spatial Logic"**—translating abstract code into visual, neurodivergent-friendly representations—and **autonomy**, allowing developers to interact via a high-level CLI while agents handle the heavy lifting.

---

## 1. System Architecture

The project utilizes a **Microservices Architecture** orchestrated via Docker Compose, ensuring isolation, scalability, and easy deployment.

### 1.1 Backend Core (`hypercode-core`)
- **Framework**: FastAPI (Python 3.11).
- **Role**: Central nervous system. Manages API endpoints (`/api/v1/tasks`), authentication (JWT), and database interactions.
- **Database**: PostgreSQL (Persistent storage for Users, Projects, Tasks).
- **Async Processing**: Celery Workers backed by Redis (Task Queue & Result Backend).

### 1.2 The Agent Swarm (Distributed Intelligence)
The swarm is the brain of the operation, routing tasks to specialized agents.

- **Routing**: The `AgentRouter` (`backend/app/agents/router.py`) intelligently dispatches tasks based on type (`translate`, `health`, `research`) or keywords.
- **The Brain**: A centralized cognitive module (`backend/app/agents/brain.py`) powered by **Perplexity AI (Sonar Pro)** for high-reasoning tasks.
- **Specialists**:
    - **Translator Agent**: Converts code into "Spatial Logic" (Markdown/Emoji-based flowcharts).
    - **Pulse Agent (The Medic)**: Monitors system health via Prometheus/Grafana.
    - **Research Agent (The Archivist)**: Generates deep-dive technical briefings.

### 1.3 Observability Stack
- **Prometheus**: Scrapes metrics from the Core, Celery, and Nodes.
- **Grafana**: Visualizes system health (CPU, Memory, Queue Depth).
- **Celery Exporter**: Exposes worker metrics to Prometheus.

---

## 2. Technology Stack

| Component | Technology |
|-----------|------------|
| **Language** | Python 3.11+ (Backend/CLI/Agents) |
| **API Framework** | FastAPI, Pydantic, SQLAlchemy |
| **Task Queue** | Celery 5.x, Redis 7 (Broker/Backend) |
| **Database** | PostgreSQL 15 (Alpine) |
| **Infrastructure** | Docker, Docker Compose |
| **Monitoring** | Prometheus, Grafana, cAdvisor, Node Exporter |
| **AI Integration** | Perplexity AI API (Sonar Pro Model) |

---

## 3. Key Functionalities & Design Patterns

### 3.1 Spatial Code Translation
*   **Pattern**: Pipeline / Transformation.
*   **Function**: Users submit raw code files via CLI. The **Translator Agent** parses the logic and outputs a "Visual Journey" Markdown file, breaking down complex logic into "Blocks," "Gates," and "Flows" with emojis.

### 3.2 Autonomous System Health Checks
*   **Pattern**: Monitoring / Observer.
*   **Function**: The **Pulse Agent** queries Prometheus directly to check the status of all containers. It returns a plain-English, "Co-Pilot" style health report (e.g., "All systems green!").

### 3.3 Automated Technical Research
*   **Pattern**: Retrieval-Augmented Generation (RAG) - simplified via Perplexity.
*   **Function**: The **Research Agent** conducts deep internet research on a given topic and synthesizes findings into a structured "Living Digital Paper".

### 3.4 CLI-First Workflow (`hypercode.py`)
*   **Pattern**: Facade.
*   **Function**: A lightweight Python CLI that wraps API interactions.
*   **Commands**:
    *   `hypercode translate <file>`
    *   `hypercode pulse`
    *   `hypercode research <topic>`
*   **Security**: Handles authentication automatically via `token.txt`.

---

## 4. Architectural Decisions (ADR Summary)

*   **ADR-001: Router Pattern**: We decoupled task submission from execution. The frontend/CLI just sends a "Task"; the Backend Router decides *who* handles it. This allows adding new agents without changing the client.
*   **ADR-002: Neurodivergent-First UX**: Output formats are strictly governed to be "Spatial," "Punchy," and "Visual" (low cognitive load) rather than dense text.
*   **ADR-003: Asynchronous Workers**: Long-running AI tasks are offloaded to Celery to keep the API responsive.

---

## 5. Scalability & Use Cases

*   **Scalability**: The worker nodes (`celery-worker`) can be horizontally scaled to handle thousands of concurrent translation/research tasks.
*   **Target Audience**: Senior developers managing complex codebases who need high-level summaries, or neurodivergent developers who struggle with dense text-based code.
