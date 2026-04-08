# 🚀 Installation Guide

Get the entire **HyperCode V2.0** ecosystem running in under 2 minutes.

> **System Requirements**
> *   **Docker Desktop** (Latest Version)
> *   **Python 3.11+**
> *   **Windows PowerShell 7+** (or WSL2/Linux/Mac equivalent)
> *   **16GB+ RAM** (Recommended for full swarm)

## 1. Clone the Repository

```powershell
git clone https://github.com/welshDog/HyperCode-V2.0.git
cd HyperCode-V2.0
```

## 2. Configure Environment

HyperCode uses a centralized `.env` file for all services.

```powershell
cp .env.example .env
```

**Edit `.env` and add your API keys:**

*   **`PERPLEXITY_API_KEY`**: Required for Agent X and most swarm agents.
*   **`PERPLEXITY_API_KEY`**: Required for the **Brain** (Cognitive Core).
*   **`OPENAI_API_KEY`**: Optional (if using OpenAI models).

## 3. Launch the Mission (Docker Compose)

We use a unified `docker-compose.yml` with profiles. The number of running services depends on which profiles you enable.

```powershell
# Start the full stack in detached mode
docker compose up -d
```

> **Note:** The first launch may take 5-10 minutes to pull images and build the local agent containers.

## 4. Verify Installation

Once the containers are running, verify the core services are healthy:

```powershell
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

You should see **`hypercode-core`**, **`celery-worker`**, **`redis`**, and **`postgres`** as `healthy`.

## 5. Access the Interfaces

*   🚀 **Mission Control Dashboard**: [http://localhost:8088](http://localhost:8088)
*   📊 **Grafana (Observability)**: [http://localhost:3001](http://localhost:3001) (User: `admin` / Pass: `admin`)
*   📝 **Core API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
*   🧠 **Crew Orchestrator**: [http://localhost:8081](http://localhost:8081)

## 6. Troubleshooting

**"Celery Worker is unhealthy"**
Check the logs:
```powershell
docker logs -f celery-worker
```
Usually caused by missing API keys or Redis connection issues.

**"Grafana shows no data"**
Ensure `celery-exporter` and `prometheus` are running:
```powershell
docker compose up -d celery-exporter prometheus
```

**"Build fails on Windows"**
Ensure Docker Desktop is running in WSL2 mode and you have sufficient disk space.
