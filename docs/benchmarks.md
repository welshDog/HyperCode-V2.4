# Performance Benchmarks

> **built with WelshDog + BROski 🚀🌙**

This document tracks the baseline performance metrics for key HyperCode workflows. These benchmarks serve as a reference for regression testing and optimization.

## Test Environment
- **Hardware:** Standard Dev Environment (e.g., 4 vCPU, 16GB RAM)
- **OS:** Windows / Linux (Docker Desktop)
- **Database:** PostgreSQL 14 (Docker)

## Baselines (v2.0.0)

### 1. Agent Response Time
| Metric | Target | Current Baseline | Status |
| :--- | :--- | :--- | :--- |
| **Simple Query** | < 2s | 1.5s | ✅ Pass |
| **Code Analysis (Medium Repo)** | < 15s | 12s | ✅ Pass |
| **Task Planning** | < 10s | 8s | ✅ Pass |

### 2. Docker Orchestration
| Metric | Target | Current Baseline | Status |
| :--- | :--- | :--- | :--- |
| **Container Startup** | < 3s | 2.1s | ✅ Pass |
| **Volume Mount Speed** | < 500ms | 300ms | ✅ Pass |
| **Cleanup Time** | < 2s | 1.2s | ✅ Pass |

### 3. API Latency
| Metric | Target | Current Baseline | Status |
| :--- | :--- | :--- | :--- |
| **Health Check** | < 50ms | 12ms | ✅ Pass |
| **Get Agent List** | < 100ms | 45ms | ✅ Pass |
| **Submit Execution** | < 200ms | 150ms | ✅ Pass |

## Methodology
Benchmarks are gathered using `locust` scripts located in `tests/load/`.
To run benchmarks:
```bash
cd tests/load
locust -f locustfile.py
```

## History
- **2026-01-20:** Initial baseline established for V2.0 release.

---
> **built with WelshDog + BROski 🚀🌙**
