# Deployment Guide

This guide covers how to deploy the HyperCode-V2.0 ecosystem using Docker Compose.

## Prerequisites

*   **Docker Desktop** (latest version)
*   **Git**
*   **Python 3.11+** (for local CLI usage)
*   **Perplexity API Key** (for the AI Brain)

## Environment Configuration

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/welshDog/HyperCode-V2.0.git
    cd HyperCode-V2.0
    ```

2.  **Environment Variables**:
    Create a `.env` file in the `backend/` directory (or root, depending on compose config).
    Required variables:
    ```ini
    PERPLEXITY_API_KEY=pplx-xxxxxxxxxxxxxxxx
    HYPERCODE_DB_URL=postgresql://postgres:postgres@postgres:5432/hypercode
    HYPERCODE_REDIS_URL=redis://redis:6379/0
    SECRET_KEY=your_secret_key_here
    ```

## Running the Swarm

### 1. Start Infrastructure
Launch the core services (Backend, Worker, DB, Redis, Monitoring):

```bash
docker-compose up --build -d
```

### 2. Verify Services
Check if all containers are healthy:

```bash
docker ps
```

You should see:
*   `hypercode-core` (Port 8000)
*   `celery-worker`
*   `postgres` (Port 5432)
*   `redis` (Port 6379)
*   `prometheus` (Port 9090)
*   `grafana` (Port 3000/3001)

### 3. Database Migration
If this is a fresh install, run migrations (usually handled by the entrypoint, but manual steps below):

```bash
docker exec -it hypercode-core alembic upgrade head
```

## Stopping the Swarm

To stop all services:

```bash
docker-compose down
```

To stop and remove volumes (reset database):

```bash
docker-compose down -v
```
