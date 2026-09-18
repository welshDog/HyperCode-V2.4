# SkillWeaver Skills Catalog 📚

Complete guide to the 19 production-ready skills available in SkillWeaver.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Code & Development Skills](#code--development-skills)
3. [Data & Analysis Skills](#data--analysis-skills)
4. [Architecture & Design Skills](#architecture--design-skills)
5. [Security & Compliance Skills](#security--compliance-skills)
6. [Performance & Monitoring Skills](#performance--monitoring-skills)
7. [Deployment & Infrastructure Skills](#deployment--infrastructure-skills)
8. [Usage Examples](#usage-examples)
9. [Composing Skills](#composing-skills)
10. [FAQ](#faq)

---

## Quick Start

### Option 1: View All Available Skills

```bash
# Start SkillWeaver first
docker compose up -d skillweaver

# View all skills in Python
python3 << 'EOF'
from services.skillweaver.skills_library import SkillLibrary
lib = SkillLibrary()
for skill in lib.get_all_skills():
    print(f"✓ {skill['name']} ({skill['skill_id']})")
EOF
```

### Option 2: Register Skills via API

```bash
# Get the skills library
curl -X GET http://localhost:8051/api/v1/skills/list

# Register a specific skill
curl -X POST http://localhost:8051/api/v1/skills/register \
  -H "Content-Type: application/json" \
  -d '{
    "skill_id": "code_review_v1",
    "name": "Code Review",
    "category": "development",
    ...
  }'
```

### Option 3: Run Examples

```bash
python3 services/skillweaver/skills_examples.py
```

---

## Code & Development Skills

### 1. **Code Review** 🔍
**Skill ID:** `code_review_v1`

Analyzes code for quality, security, performance, and best practices.

**Inputs:**
```json
{
  "code": "string (source code)",
  "language": "python|javascript|go|rust",
  "focus_areas": ["quality", "security", "performance", "style"],
  "context": "project context (optional)"
}
```

**Outputs:**
```json
{
  "quality_score": 85,
  "issues": [
    {
      "type": "complexity",
      "severity": "warning",
      "line": 42,
      "suggestion": "Break into smaller functions"
    }
  ],
  "refactored_code": "improved code",
  "metrics": {
    "cyclomatic_complexity": 8,
    "maintainability_index": 72
  }
}
```

**Performance:**
- ⏱️ ~3000ms
- 💰 250 tokens

**Use Cases:**
- PR code reviews
- Quality gates
- Pre-commit checks
- CI/CD pipelines

---

### 2. **Test Generation** ✅
**Skill ID:** `test_generation_v1`

Generates unit tests, integration tests, and edge case coverage.

**Inputs:**
```json
{
  "code": "function or class code",
  "language": "python|javascript|go",
  "coverage_target": 85,
  "test_framework": "pytest|jest|gotest"
}
```

**Outputs:**
```json
{
  "test_code": "complete test file",
  "test_cases": [
    {
      "name": "test_basic_flow",
      "description": "Tests happy path",
      "coverage": 60
    }
  ],
  "coverage_estimate": 87,
  "edge_cases_covered": ["null input", "empty list", "timeout"]
}
```

**Performance:**
- ⏱️ ~2500ms
- 💰 200 tokens

**Use Cases:**
- TDD (Test-Driven Development)
- Coverage improvement
- Regression test generation
- Documentation through tests

---

### 3. **Bug Detection** 🐛
**Skill ID:** `bug_detection_v1`

Identifies potential bugs, memory leaks, race conditions, logic errors.

**Inputs:**
```json
{
  "code": "code to analyze",
  "language": "python|javascript|go|rust",
  "severity": "critical|high|medium|low"
}
```

**Outputs:**
```json
{
  "bugs_found": 3,
  "bug_list": [
    {
      "type": "null_pointer_dereference",
      "severity": "critical",
      "line": 15,
      "description": "Potential null reference",
      "fix": "Add null check before access"
    }
  ],
  "risk_level": "high",
  "suggested_fixes": ["Add validation", "Use optional type"]
}
```

**Performance:**
- ⏱️ ~4000ms
- 💰 300 tokens

**Use Cases:**
- Pre-production checks
- Security scanning
- Code quality gates
- Static analysis

---

### 4. **Documentation** 📖
**Skill ID:** `documentation_skill_v1`

Creates detailed documentation, docstrings, API docs.

**Inputs:**
```json
{
  "code": "source code",
  "language": "python|javascript|go",
  "doc_format": "markdown|rst|html|docstring",
  "detail_level": "basic|standard|comprehensive"
}
```

**Outputs:**
```json
{
  "documentation": "formatted documentation",
  "api_docs": "API reference",
  "examples": [
    "# Basic Usage\nfrom module import function\nresult = function()",
    "# Advanced Usage\nwith options as opts: ..."
  ],
  "diagrams": ["ASCII diagram of flow"]
}
```

**Performance:**
- ⏱️ ~2000ms
- 💰 180 tokens

**Use Cases:**
- Auto-generating docs
- API documentation
- README generation
- Docstring updates

---

### 5. **Code Optimization** ⚡
**Skill ID:** `optimization_v1`

Identifies and implements performance optimizations.

**Inputs:**
```json
{
  "code": "code to optimize",
  "language": "python|javascript|go",
  "target_metric": "speed|memory|io|cpu",
  "constraints": {"max_complexity": 10}
}
```

**Outputs:**
```json
{
  "optimized_code": "improved code",
  "improvements": {
    "speed_gain_percent": 45,
    "memory_saved_mb": 128
  },
  "techniques_applied": [
    "Memoization",
    "Loop unrolling",
    "Lazy loading"
  ],
  "benchmarks_before": {"avg_ms": 500},
  "benchmarks_after": {"avg_ms": 275}
}
```

**Performance:**
- ⏱️ ~3500ms
- 💰 280 tokens

**Use Cases:**
- Performance tuning
- Bottleneck elimination
- Memory optimization
- Scaling preparation

---

## Data & Analysis Skills

### 6. **Data Analysis** 📊
**Skill ID:** `data_analysis_v1`

Analyzes datasets for patterns, anomalies, and insights.

**Inputs:**
```json
{
  "data": "CSV|JSON|structured data",
  "data_format": "csv|json|parquet",
  "analysis_type": "summary|correlation|distribution|anomaly",
  "sample_size": 10000
}
```

**Outputs:**
```json
{
  "summary_stats": {
    "mean": 42.5,
    "median": 40,
    "std": 15.2,
    "q1": 25,
    "q3": 60
  },
  "insights": [
    "Bimodal distribution detected",
    "Positive correlation with feature_x"
  ],
  "anomalies": [
    {"value": 999, "severity": "high", "zscore": 4.2}
  ],
  "correlations": [
    {"vars": ["a", "b"], "coefficient": 0.87}
  ]
}
```

**Performance:**
- ⏱️ ~5000ms
- 💰 350 tokens

**Use Cases:**
- Exploratory data analysis
- Anomaly detection
- Feature engineering
- Business intelligence

---

### 7. **Trend Prediction** 🔮
**Skill ID:** `trend_prediction_v1`

Forecasts future trends using historical data and ML models.

**Inputs:**
```json
{
  "historical_data": [100, 105, 110, 108, 115, 120],
  "forecast_periods": 12,
  "confidence_level": 0.95,
  "model_type": "arima|exponential_smoothing|prophet"
}
```

**Outputs:**
```json
{
  "forecast": [125, 130, 128, 135, 140, 138],
  "confidence_intervals": {
    "upper": [135, 145, 142, 152, 160, 155],
    "lower": [115, 115, 114, 118, 120, 121]
  },
  "trend_direction": "up",
  "accuracy_score": 0.92,
  "model_used": "prophet"
}
```

**Performance:**
- ⏱️ ~4000ms
- 💰 320 tokens

**Use Cases:**
- Sales forecasting
- Resource planning
- Capacity planning
- Time-series analysis

---

### 8. **Data Cleaning** 🧹
**Skill ID:** `data_cleaning_v1`

Cleans and standardizes messy data.

**Inputs:**
```json
{
  "data": "raw data",
  "data_format": "csv|json",
  "cleaning_rules": {"null_policy": "drop"},
  "handle_missing": "drop|mean|forward_fill|interpolate"
}
```

**Outputs:**
```json
{
  "cleaned_data": "processed data",
  "issues_found": 45,
  "issue_report": {
    "duplicates": 12,
    "missing_values": 28,
    "outliers": 5
  },
  "quality_score": 92,
  "transformations_applied": [
    "Removed 12 duplicates",
    "Filled 28 NaN values with mean",
    "Removed 5 outliers (>3σ)"
  ]
}
```

**Performance:**
- ⏱️ ~2500ms
- 💰 200 tokens

**Use Cases:**
- Data preprocessing
- ETL pipelines
- Data validation
- Quality assurance

---

## Architecture & Design Skills

### 9. **Architecture Design** 🏗️
**Skill ID:** `architecture_design_v1`

Creates scalable, maintainable system architectures.

**Inputs:**
```json
{
  "requirements": "Build a real-time chat system",
  "scale": "medium|large|enterprise",
  "constraints": {
    "budget": "medium",
    "latency_ms": 100,
    "throughput_rps": 10000
  },
  "existing_stack": ["Python", "PostgreSQL", "Redis"]
}
```

**Outputs:**
```json
{
  "architecture": {
    "components": ["API Gateway", "Message Queue", "Cache"],
    "interactions": "Request -> Queue -> Workers"
  },
  "diagram": "ASCII or Mermaid diagram",
  "component_specs": [
    {
      "name": "API Gateway",
      "responsibility": "Request routing",
      "tech": "FastAPI on Kubernetes"
    }
  ],
  "scaling_strategy": {
    "horizontal": "Add more replicas",
    "vertical": "Increase instance size"
  },
  "recommendations": ["Use CDN", "Enable caching", "Add load balancer"]
}
```

**Performance:**
- ⏱️ ~4500ms
- 💰 400 tokens

**Use Cases:**
- System design
- Architecture reviews
- Scaling planning
- Technology selection

---

### 10. **Design Pattern Expert** 🎯
**Skill ID:** `design_pattern_v1`

Recommends and implements design patterns.

**Inputs:**
```json
{
  "problem_description": "How do I manage object creation?",
  "language": "python|javascript|go|java",
  "context": "Factory pattern needed"
}
```

**Outputs:**
```json
{
  "recommended_patterns": [
    {
      "pattern": "Factory Pattern",
      "suitability": 95,
      "description": "Best for object creation"
    }
  ],
  "implementation": "class code example",
  "pros": ["Loose coupling", "Easy to extend"],
  "cons": ["Slight overhead", "More classes"],
  "alternatives": ["Singleton", "Builder"]
}
```

**Performance:**
- ⏱️ ~2000ms
- 💰 180 tokens

**Use Cases:**
- Design consultations
- Code reviews
- Architecture decisions
- Refactoring guidance

---

### 11. **API Design** 🔌
**Skill ID:** `api_design_v1`

Designs well-structured APIs (REST, GraphQL).

**Inputs:**
```json
{
  "resource_description": "User management system",
  "api_style": "rest|graphql|grpc",
  "authentication": "oauth2|jwt|api_key",
  "version": "v1"
}
```

**Outputs:**
```json
{
  "api_spec": "OpenAPI schema",
  "endpoints": [
    {
      "method": "GET",
      "path": "/users",
      "description": "List all users"
    }
  ],
  "authentication_flow": "OAuth2 with JWT tokens",
  "rate_limiting": "100 requests/minute per user",
  "documentation": "Markdown docs"
}
```

**Performance:**
- ⏱️ ~2500ms
- 💰 220 tokens

**Use Cases:**
- API design
- OpenAPI spec generation
- Integration planning
- Client library generation

---

## Security & Compliance Skills

### 12. **Security Audit** 🔐
**Skill ID:** `security_audit_v1`

Performs comprehensive security audits.

**Inputs:**
```json
{
  "code": "source code",
  "language": "python|javascript|go",
  "frameworks": ["django", "fastapi"],
  "audit_depth": "light|standard|deep"
}
```

**Outputs:**
```json
{
  "vulnerabilities": [
    {
      "type": "SQL Injection",
      "severity": "critical",
      "cwe": "CWE-89",
      "line": 42,
      "fix": "Use parameterized queries"
    }
  ],
  "security_score": 68,
  "critical_issues": 2,
  "compliance_gaps": ["OWASP A1", "OWASP A2"],
  "remediation_plan": {
    "priority": "critical",
    "effort": "2 hours",
    "description": "Fix SQL injection vulnerabilities"
  }
}
```

**Performance:**
- ⏱️ ~5000ms
- 💰 400 tokens

**Use Cases:**
- Penetration testing
- Pre-release security checks
- Compliance verification
- Vulnerability assessment

---

### 13. **Compliance Checker** ✅
**Skill ID:** `compliance_check_v1`

Verifies compliance with regulations (GDPR, HIPAA, SOC2, PCI-DSS).

**Inputs:**
```json
{
  "code": "source code",
  "regulations": ["gdpr", "hipaa", "soc2"],
  "context": "Healthcare application"
}
```

**Outputs:**
```json
{
  "compliance_status": {
    "gdpr": "compliant",
    "hipaa": "non_compliant",
    "soc2": "partial"
  },
  "gaps": [
    {
      "regulation": "HIPAA",
      "gap": "Missing encryption at rest",
      "severity": "critical",
      "fix": "Implement AES-256 encryption"
    }
  ],
  "audit_trail": "Compliance documentation",
  "recommendations": ["Enable audit logging"]
}
```

**Performance:**
- ⏱️ ~3000ms
- 💰 300 tokens

**Use Cases:**
- Regulatory compliance
- Audit preparation
- Data protection verification
- Legal requirements

---

## Performance & Monitoring Skills

### 14. **Performance Profiler** 📈
**Skill ID:** `performance_profiling_v1`

Profiles code performance and identifies bottlenecks.

**Inputs:**
```json
{
  "code": "function or module",
  "language": "python|javascript|go",
  "profile_type": "cpu|memory|io",
  "iterations": 1000
}
```

**Outputs:**
```json
{
  "hotspots": [
    {
      "function": "process_data",
      "time_percent": 65,
      "calls": 1000,
      "avg_ms": 0.65
    }
  ],
  "total_time": 650,
  "memory_peak": 256,
  "bottleneck_report": "process_data() is main bottleneck",
  "optimization_suggestions": [
    "Cache intermediate results",
    "Use vectorization instead of loops"
  ]
}
```

**Performance:**
- ⏱️ ~3500ms
- 💰 250 tokens

**Use Cases:**
- Performance debugging
- Optimization identification
- Capacity planning
- Benchmark analysis

---

### 15. **Monitoring Setup** 📡
**Skill ID:** `monitoring_setup_v1`

Configures monitoring, logging, and alerting.

**Inputs:**
```json
{
  "application": "my_service",
  "platform": "kubernetes|docker|serverless",
  "metrics": ["cpu", "memory", "latency", "errors"],
  "alert_thresholds": {"cpu": 80, "memory": 90}
}
```

**Outputs:**
```json
{
  "prometheus_config": "scrape_configs: ...",
  "grafana_dashboard": "{dashboard JSON}",
  "alerting_rules": "alert MyAlert if cpu > 80",
  "logging_config": "fluent_bit config",
  "setup_instructions": "Step-by-step guide"
}
```

**Performance:**
- ⏱️ ~2500ms
- 💰 220 tokens

**Use Cases:**
- Observability setup
- Alert configuration
- Dashboard creation
- Ops automation

---

## Deployment & Infrastructure Skills

### 16. **Docker Optimizer** 🐳
**Skill ID:** `docker_optimization_v1`

Optimizes Dockerfiles for size, build time, security.

**Inputs:**
```json
{
  "dockerfile": "FROM python:3.11\n...",
  "application_type": "python|node|go|rust",
  "target_size": "minimal|small|medium"
}
```

**Outputs:**
```json
{
  "optimized_dockerfile": "improved Dockerfile",
  "size_reduction": 45,
  "build_time_reduction": 30,
  "security_improvements": [
    "Use distroless images",
    "Run as non-root user"
  ],
  "recommendations": [
    "Use multi-stage builds",
    "Minimize layer count"
  ]
}
```

**Performance:**
- ⏱️ ~1500ms
- 💰 150 tokens

**Use Cases:**
- Image optimization
- Build speed improvement
- Security hardening
- Cost reduction

---

### 17. **Kubernetes Deployment** ☸️
**Skill ID:** `kubernetes_deployment_v1`

Creates production-ready Kubernetes manifests.

**Inputs:**
```json
{
  "application": "my_app",
  "image": "my_app:latest",
  "replicas": 3,
  "resource_limits": {"cpu": "500m", "memory": "512Mi"},
  "ingress_domain": "app.example.com"
}
```

**Outputs:**
```json
{
  "deployment_manifest": "apiVersion: apps/v1\nkind: Deployment\n...",
  "service_manifest": "apiVersion: v1\nkind: Service\n...",
  "ingress_manifest": "apiVersion: networking.k8s.io/v1\n...",
  "hpa_manifest": "Autoscaling rules",
  "deployment_guide": "How to deploy"
}
```

**Performance:**
- ⏱️ ~2000ms
- 💰 180 tokens

**Use Cases:**
- K8s deployments
- Manifest generation
- Infrastructure as code
- CI/CD integration

---

### 18. **CI/CD Setup** 🚀
**Skill ID:** `ci_cd_setup_v1`

Configures CI/CD pipelines (GitHub Actions, GitLab, Jenkins).

**Inputs:**
```json
{
  "platform": "github|gitlab|jenkins",
  "language": "python|javascript|go",
  "stages": ["lint", "test", "build", "deploy"],
  "target_environment": "staging|production"
}
```

**Outputs:**
```json
{
  "pipeline_config": ".github/workflows/deploy.yml",
  "test_stage": "pytest --cov=.",
  "build_stage": "docker build -t app:latest .",
  "deploy_stage": "kubectl apply -f manifests/",
  "secrets_required": ["DOCKER_TOKEN", "KUBE_CONFIG"]
}
```

**Performance:**
- ⏱️ ~2000ms
- 💰 180 tokens

**Use Cases:**
- Pipeline creation
- Automation setup
- Deploy workflows
- Release management

---

## Usage Examples

### Example 1: Register a Skill

```bash
curl -X POST http://localhost:8051/api/v1/skills/register \
  -H "Content-Type: application/json" \
  -d '{
    "skill_id": "code_review_v1",
    "name": "Code Review",
    "category": "development",
    "inputs": {
      "code": "str",
      "language": "str"
    },
    "outputs": {
      "quality_score": "int",
      "issues": "list"
    }
  }'
```

### Example 2: Search for Skills

```bash
# By tag
curl -X GET "http://localhost:8051/api/v1/skills/search?tag=security"

# By category
curl -X GET "http://localhost:8051/api/v1/skills/search?category=development"

# By name
curl -X GET "http://localhost:8051/api/v1/skills/search?query=optimization"
```

### Example 3: Get Skill Details

```bash
curl -X GET "http://localhost:8051/api/v1/skills/code_review_v1"
```

### Example 4: List All Skills

```bash
curl -X GET "http://localhost:8051/api/v1/skills/list"
```

### Example 5: Get Statistics

```bash
curl -X GET "http://localhost:8051/api/v1/stats"
```

---

## Composing Skills

### Create a Workflow

Skills can be composed into multi-step workflows:

```bash
curl -X POST http://localhost:8051/api/v1/skills/compose \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "code_quality_pipeline",
    "name": "Code Quality Pipeline",
    "steps": [
      {
        "step": 1,
        "skill_id": "code_review_v1",
        "inputs": {
          "code": "${input.code}",
          "language": "${input.language}",
          "focus_areas": ["security", "performance"]
        }
      },
      {
        "step": 2,
        "skill_id": "test_generation_v1",
        "inputs": {
          "code": "${step_1.outputs.refactored_code}",
          "language": "${input.language}"
        }
      },
      {
        "step": 3,
        "skill_id": "security_audit_v1",
        "inputs": {
          "code": "${input.code}",
          "language": "${input.language}",
          "audit_depth": "standard"
        }
      }
    ]
  }'
```

---

## FAQ

### Q: How many skills are available?
**A:** 19 production-ready skills across 6 categories.

### Q: What languages are supported?
**A:** Python, JavaScript, Go, Rust (varies by skill)

### Q: Can I create custom skills?
**A:** Yes, extend `SkillLibrary` and add your own skills.

### Q: What's the cost of using skills?
**A:** Each skill has a token cost (150-400 tokens). Shown in skill definition.

### Q: How do I register multiple skills at once?
**A:** Use the bulk registration endpoint or iterate through skills.

### Q: Can skills be composed?
**A:** Yes, use the `/compose` endpoint to create multi-step workflows.

### Q: What's the performance?
**A:** Skills execute in 1.5-5 seconds. See individual skill timing.

### Q: How do I handle skill dependencies?
**A:** SkillWeaver automatically manages dependencies during composition.

### Q: Can agents discover skills dynamically?
**A:** Yes, use the `/search` endpoint with tags, categories, or queries.

### Q: How do I monitor skill usage?
**A:** Use `/stats` endpoint to get aggregated metrics.

---

**Created:** 2026-04-22  
**Version:** 1.0  
**Status:** Production Ready ✅
