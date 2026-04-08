# Developer Onboarding Guide

Welcome to **HyperCode-V2.0**! 🚀 This guide will help you get set up and contributing to the swarm.

## 1. The Philosophy
We build for **Neurodivergent Minds**.
*   **Spatial Logic**: Code should be visual.
*   **Low Cognitive Load**: Documentation is punchy and structured.
*   **Autonomy**: Agents do the heavy lifting; we guide them.

## 2. Setting Up Your Dev Environment

### Tools Needed
*   VS Code
*   Docker Desktop
*   Python 3.11

### Initial Setup
1.  **Clone & Install**:
    ```bash
    git clone https://github.com/welshDog/HyperCode-V2.0.git
    cd HyperCode-V2.0
    ```

2.  **Virtual Environment**:
    It's recommended to create a venv for local CLI usage:
    ```bash
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1  # Windows (PowerShell)
    pip install requests
    ```

3.  **Auth Token**:
    You need a `token.txt` to use the CLI.
    *   If you have a seed script, run it.
    *   Otherwise, log in to `http://localhost:8000/docs` (Authorize button) and copy the token into `token.txt`.

## 3. Project Structure

*   `backend/`: The FastAPI core.
    *   `app/agents/`: Where the AI logic lives (`translator.py`, `pulse.py`, `researcher.py`).
    *   `app/api/`: REST endpoints.
    *   `app/worker.py`: Celery task definitions.
*   `hypercode.py`: The CLI tool.
*   `docs/`: Documentation (You are here).

## 4. How to Contribute

### Adding a New Agent
1.  Create `backend/app/agents/new_agent.py`.
2.  Implement a class with a `process(payload)` method.
3.  Register it in `backend/app/agents/router.py`.
4.  Add a command to `hypercode.py` to trigger it.

### Running Tests
We use `pytest`.
```bash
cd backend
pytest
```

## 5. Communication
*   **Issues**: Check GitHub Issues for tasks.
*   **Style**: Keep code comments clean and "Bro-friendly".

Go forth and build! 🌍
