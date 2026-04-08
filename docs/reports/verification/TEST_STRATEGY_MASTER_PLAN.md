# HyperCode Master Test Strategy

## 1. Overview
This document outlines the comprehensive testing strategy for the HyperCode multi-agent ecosystem. Our goal is to ensure high reliability, rapid feedback loops, and confident deployments through a layered testing approach.

## 2. Testing Layers (Pyramid Strategy)

### 2.1 Unit Tests (Foundational Layer)
- **Scope**: Individual functions, classes, and components in isolation.
- **Coverage Target**: >80% code coverage.
- **Tools**:
  - **Backend (Python)**: `pytest`, `pytest-cov`, `unittest.mock`.
  - **Frontend (React)**: `Vitest`, `React Testing Library`.
- **Key Areas**:
  - **Orchestrator**: Task routing logic, state transitions, API request validation.
  - **Agent Factory**: Blueprint parsing, ID generation, registry operations.
  - **Dashboard**: Component rendering, hook logic (e.g., `useWebSocket`), utility functions.

### 2.2 Integration Tests (Service Layer)
- **Scope**: Interactions between modules and external services (mocked or containerized).
- **Tools**: `pytest-asyncio`, `TestContainers` (optional), `httpx`.
- **Key Areas**:
  - **Orchestrator <-> Redis**: verifying task persistence and pub/sub.
  - **Factory <-> Registry**: ensuring agents are correctly registered/deregistered.
  - **Dashboard <-> API**: verifying data fetching and error handling.

### 2.3 End-to-End (E2E) Tests (Workflow Layer)
- **Scope**: Full system workflows from user input to final output.
- **Tools**: `Playwright` (future), Shell-based smoke tests (current).
- **Scenarios**:
  - **"Build a Todo App"**: User sends command -> Orchestrator plans -> Agents execute -> Result returned.
  - **"Approval Flow"**: User sends risky command -> Approval Modal appears -> User approves -> Execution proceeds.

## 3. Automated Pipelines (CI/CD)

We utilize **GitHub Actions** to enforce quality gates on every push to `main` and every Pull Request.

### Workflow: `ci.yml`
1. **Linting**:
   - Python: `ruff check .`
   - TypeScript: `npm run lint`
2. **Testing**:
   - Backend: `pytest --cov=agents`
   - Frontend: `npm test`
3. **Build**:
   - Verify Docker images build successfully.
   - Verify Next.js app builds (`npm run build`).

## 4. Test Data Management
- **Mocking**: Use `unittest.mock` for external API calls (e.g., OpenAI, PERPLEXITY) to avoid costs and flakiness during unit tests.
- **Fixtures**: Use `pytest` fixtures for common setups (e.g., initialized Orchestrator app, mock Redis client).

## 5. Performance Testing
- **Tool**: `k6` or `locust`.
- **Scenario**: Simulate 100 concurrent agent spawn requests to the Factory.
- **Success Criteria**: p95 latency < 500ms.

## 6. Success Criteria for Release
- [ ] All unit and integration tests pass.
- [ ] Code coverage > 80%.
- [ ] No critical/high security vulnerabilities (verified by `trivy` or similar).
- [ ] Successful build of all Docker containers.

## 7. Execution Guide

### Running Backend Tests
```bash
cd agents/crew-orchestrator
pytest
```

### Running Frontend Tests
```bash
cd agents/dashboard
npm test
```
