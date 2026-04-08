# 🧪 Testing Guide

This guide covers testing for the **HyperCode V2.0 Backend** and related services.

> **Test Stack**
> *   **pytest**: Test Runner
> *   **pytest-asyncio**: Async Test Support
> *   **httpx**: Async HTTP Client
> *   **ruff**: Fast Python Linter
> *   **pip-audit**: Dependency Vulnerability Scanner

## 1. Running Tests Locally

### Prerequisites
Ensure you have the development dependencies installed:

```powershell
cd backend
pip install -r requirements-dev.txt
```

### Run Tests (Backend)
Execute the full test suite with coverage:

```powershell
pytest -v --cov=app --cov-report=term-missing
```

### Run Specific Tests
To run only the health check tests:

```powershell
pytest -k "test_health_check"
```

## 2. CI/CD Pipeline

The project uses **GitHub Actions** for Continuous Integration.

**Workflow File**: `.github/workflows/ci-python.yml`

### Pipeline Stages
1.  **Checkout**: Clones the repository.
2.  **Install Deps**: Installs `requirements.txt` and `requirements-dev.txt`.
3.  **Run Tests**: Executes `pytest` with coverage tracking.
4.  **Coverage Check**: Fails if coverage drops below the threshold (currently 10%).
5.  **Audit**: Scans dependencies for known vulnerabilities (`pip-audit`, `safety`).

## 3. Writing New Tests

### Structure
All tests reside in `backend/app/tests/`.

```python
# backend/app/tests/test_example.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_example_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/example")
    assert response.status_code == 200
```

### Mocking Dependencies
Use `unittest.mock` or `pytest-mock` to mock external services (e.g., Database, Redis, Brain API).

## 4. Troubleshooting Tests

**"ModuleNotFoundError: No module named 'app'"**
Ensure you are running `pytest` from the `backend/` directory, or set `PYTHONPATH`:

```powershell
$env:PYTHONPATH="C:\path\to\HyperCode-V2.0\backend"
pytest
```

**"Asyncio Loop Error"**
Ensure your test functions are marked with `@pytest.mark.asyncio`.
