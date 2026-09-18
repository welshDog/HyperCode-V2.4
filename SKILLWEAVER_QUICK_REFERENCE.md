# ⚡ SkillWeaver Skills Quick Reference

**19 Production-Ready Skills** • **6 Categories** • **Ready to Use**

---

## 🎯 Skills by Category

### 📝 Development (5 skills)

| Skill | ID | Cost | Time | Use For |
|-------|-----|------|------|---------|
| Code Review | `code_review_v1` | 250 🪙 | 3s ⏱️ | Quality gates, PR review |
| Test Generation | `test_generation_v1` | 200 🪙 | 2.5s ⏱️ | Coverage, TDD |
| Bug Detection | `bug_detection_v1` | 300 🪙 | 4s ⏱️ | Vulnerabilities, logic errors |
| Documentation | `documentation_v1` | 180 🪙 | 2s ⏱️ | API docs, README, docstrings |
| Optimization | `optimization_v1` | 280 🪙 | 3.5s ⏱️ | Performance tuning |

### 📊 Analytics (3 skills)

| Skill | ID | Cost | Time | Use For |
|-------|-----|------|------|---------|
| Data Analysis | `data_analysis_v1` | 350 🪙 | 5s ⏱️ | Patterns, anomalies |
| Trend Prediction | `trend_prediction_v1` | 320 🪙 | 4s ⏱️ | Forecasting, time-series |
| Data Cleaning | `data_cleaning_v1` | 200 🪙 | 2.5s ⏱️ | ETL, quality assurance |

### 🏗️ Architecture (3 skills)

| Skill | ID | Cost | Time | Use For |
|-------|-----|------|------|---------|
| Architecture Design | `architecture_design_v1` | 400 🪙 | 4.5s ⏱️ | System design, scaling |
| Design Patterns | `design_pattern_v1` | 180 🪙 | 2s ⏱️ | Best practices, refactoring |
| API Design | `api_design_v1` | 220 🪙 | 2.5s ⏱️ | REST, GraphQL, OpenAPI |

### 🔐 Security (2 skills)

| Skill | ID | Cost | Time | Use For |
|-------|-----|------|------|---------|
| Security Audit | `security_audit_v1` | 400 🪙 | 5s ⏱️ | Vulnerability scanning |
| Compliance Check | `compliance_check_v1` | 300 🪙 | 3s ⏱️ | GDPR, HIPAA, SOC2 |

### 📈 Performance (2 skills)

| Skill | ID | Cost | Time | Use For |
|-------|-----|------|------|---------|
| Performance Profiler | `performance_profiling_v1` | 250 🪙 | 3.5s ⏱️ | Bottleneck detection |
| Monitoring Setup | `monitoring_setup_v1` | 220 🪙 | 2.5s ⏱️ | Observability, alerts |

### 🚀 DevOps (3 skills)

| Skill | ID | Cost | Time | Use For |
|-------|-----|------|------|---------|
| Docker Optimizer | `docker_optimization_v1` | 150 🪙 | 1.5s ⏱️ | Image size, build speed |
| K8s Deployment | `kubernetes_deployment_v1` | 180 🪙 | 2s ⏱️ | Manifests, scaling |
| CI/CD Setup | `ci_cd_setup_v1` | 180 🪙 | 2s ⏱️ | Pipelines, automation |

---

## 🔥 Most Popular Skills

### ⭐ Top 3 by Usage
1. **Code Review** — Universal quality checking
2. **Security Audit** — Compliance & vulnerability scanning
3. **Docker Optimizer** — Container best practices

### ⚡ Fastest Skills
1. **Docker Optimizer** — 1.5s (lightweight analysis)
2. **Design Patterns** — 2s (pattern matching)
3. **Documentation** — 2s (template-based)

### 💰 Most Expensive Skills
1. **Architecture Design** — 400 tokens (deep analysis)
2. **Security Audit** — 400 tokens (comprehensive scanning)
3. **Data Analysis** — 350 tokens (statistical modeling)

---

## 🎯 Agent Skill Recommendations

### Code Reviewer Agent
```
✓ Code Review
✓ Bug Detection
✓ Test Generation
✓ Security Audit
💰 Total: 1050 tokens
```

### System Architect
```
✓ Architecture Design
✓ API Design
✓ Design Patterns
✓ Performance Profiler
💰 Total: 830 tokens
```

### DevOps Engineer
```
✓ Docker Optimizer
✓ K8s Deployment
✓ CI/CD Setup
✓ Monitoring Setup
💰 Total: 730 tokens
```

### Data Scientist
```
✓ Data Analysis
✓ Trend Prediction
✓ Data Cleaning
✓ Performance Profiler
💰 Total: 1120 tokens
```

---

## 📡 API Quick Commands

### Register a Skill
```bash
curl -X POST http://localhost:8051/api/v1/skills/register \
  -d @skill.json \
  -H "Content-Type: application/json"
```

### Search Skills
```bash
# By tag
curl "http://localhost:8051/api/v1/skills/search?tag=security"

# By category
curl "http://localhost:8051/api/v1/skills/search?category=development"

# All
curl "http://localhost:8051/api/v1/skills/list"
```

### Get Statistics
```bash
curl "http://localhost:8051/api/v1/stats"
```

### Compose Workflow
```bash
curl -X POST http://localhost:8051/api/v1/skills/compose \
  -d @workflow.json \
  -H "Content-Type: application/json"
```

---

## 🎓 Learning Path

### Day 1: Foundation
- [ ] Deploy SkillWeaver
- [ ] List all skills
- [ ] Register 3 skills manually
- [ ] Test via Swagger UI (http://localhost:8051/docs)

### Day 2: Integration
- [ ] Integrate one agent with CodeReview skill
- [ ] Register all Development skills
- [ ] Test skill discovery
- [ ] Create first skill composition

### Day 3: Production
- [ ] Bulk register all skills
- [ ] Set up monitoring
- [ ] Create agent-specific skill sets
- [ ] Monitor usage via stats endpoint

---

## 💡 Pro Tips

### Tip 1: Combine Skills
Most powerful when composed:
- Code Review → Test Generation → Security Audit
- Data Analysis → Trend Prediction → Monitoring Setup

### Tip 2: Cost Optimization
- Use fast, cheap skills for pre-checks (Docker Optimizer)
- Reserve expensive skills for final verification (Security Audit)

### Tip 3: Language Support
Each skill supports multiple languages — check individual specs.

### Tip 4: Caching
Skills with same inputs can be cached in Redis (automatic).

### Tip 5: Parallel Execution
Multiple independent skills can run in parallel for speed.

---

## 🔗 Related Resources

- **Full Catalog:** `SKILLWEAVER_SKILLS_CATALOG.md`
- **Examples:** `services/skillweaver/skills_examples.py`
- **Library:** `services/skillweaver/skills_library.py`
- **API Docs:** http://localhost:8051/docs
- **Integration Guide:** `SKILLWEAVER_INTEGRATION.md`

---

## 📞 Support

### Common Issues

**Q: Skill not found?**
```bash
# Check skill exists
curl "http://localhost:8051/api/v1/skills/{skill_id}"
```

**Q: Registration failed?**
```bash
# Check SkillWeaver is running
docker logs skillweaver

# Verify Redis connection
docker logs redis
```

**Q: Execution timeout?**
```bash
# Use faster skill or increase timeout
# See individual skill timing in catalog
```

---

## 📊 Dashboard

Check skill usage at: **http://localhost:8051/api/v1/stats**

Shows:
- Total skills registered
- Skills by category
- Most used skills
- Average response time
- Total tokens consumed

---

**Last Updated:** 2026-04-22  
**Version:** 1.0  
**Status:** ✅ Production Ready

Use this guide to quickly find and use any skill!
