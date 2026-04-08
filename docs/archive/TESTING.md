# Testing Strategy

## Overview
This document outlines the comprehensive testing strategy for the HyperCode V2.0 application logic. The strategy employs a pyramid approach, prioritizing fast, isolated unit tests while ensuring system reliability through integration and end-to-end (E2E) tests.

## Test Levels

### 1. Unit Tests (`tests/unit/`)
- **Scope**: Individual functions, classes, and methods in isolation.
- **Dependencies**: All external dependencies (Database, Redis, External APIs) must be mocked.
- **Goal**: Verify logic correctness, edge case handling, and error handling.
- **Coverage Target**: >80% code coverage.

### 2. Integration Tests (`tests/e2e/`)
- **Scope**: Interaction between multiple components (e.g., API -> Service -> Database).
- **Dependencies**: 
  - **Database**: Real Postgres instance (Dockerized) or strictly schema-compliant mock.
  - **Redis**: Real Redis instance (Dockerized) or `fakeredis`.
  - **External APIs**: Mocked (e.g., OpenAI API).
- **Goal**: Verify component wiring, data persistence, and transaction integrity.

### 3. End-to-End (E2E) Tests
- **Scope**: Full user workflows from entry point (API/Frontend) to effect.
- **Dependencies**: Full Docker Compose environment.
- **Goal**: Validate critical business flows (e.g., "Register Agent", "Execute Mission").

### 4. Performance Tests (`tests/perf/`)
- **Scope**: Critical path latency and throughput.
- **Goal**: Ensure P95 latency stays within SLAs (e.g., <200ms for API responses).

## Infrastructure & Tooling

- **Test Runner**: `pytest`
- **Async Support**: `pytest-asyncio`
- **Coverage**: `pytest-cov` (HTML and XML reports)
- **Mocking**: `unittest.mock`, `fakeredis`, `respx` (for HTTP APIs).
- **CI/CD**: GitHub Actions (defined in `.github/workflows/test.yml`).

## Running Tests

### Local Environment
Run tests inside the `hypercode-core` container to ensure correct environment and dependencies:

```bash
docker compose exec hypercode-core pytest
```

### Coverage Report
Coverage reports are generated automatically in `htmlcov/` and `coverage.xml`.
To check coverage percentage:

```bash
docker compose exec hypercode-core coverage report
```

## Continuous Integration
The CI pipeline executes on every push to `main` and pull requests.
1.  **Build**: Build Docker images.
2.  **Test**: Run `pytest` with coverage.
3.  **Lint**: Check code style (optional).
4.  **Report**: Publish test results and coverage artifacts.

## Current Status & Roadmap
- **Current Coverage**: ~23% (Baseline established).
- **Immediate Goal**: Increase coverage for `AgentRegistry`, `Orchestrator`, and `VoiceService`.
- **Defect Tracking**: Failed tests are tracked as high-priority bugs.
