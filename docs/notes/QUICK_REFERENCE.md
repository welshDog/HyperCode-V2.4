# HyperAIFS - Quick Reference Card

## 🚀 Start System

```bash
cd hyperaifs
export OPENAI_API_KEY="sk-..."
docker-compose -f infra/docker/docker-compose.yml up -d
```

## 📍 Service URLs

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |
| Health | http://localhost:8000/health |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |
| Qdrant | http://localhost:6333 |

## 📤 Upload File

```bash
curl -X POST http://localhost:8000/api/files/upload \
  -F "file=@document.pdf" \
  -F "project_id=1"
```

## 🔍 Search Files

```bash
curl -X POST http://localhost:8000/api/files/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "python automation",
    "limit": 20
  }'
```

## 🏷️ Tag File

```bash
curl -X POST http://localhost:8000/api/files/1/tags \
  -H "Content-Type: application/json" \
  -d '{"tag_name": "important"}'
```

## 📋 List Files

```bash
curl http://localhost:8000/api/projects/1/files?limit=50&tags=python
```

## 🗑️ Delete File

```bash
curl -X DELETE http://localhost:8000/api/files/1
```

## 🔄 Reorganize Project

```bash
curl -X POST http://localhost:8000/api/projects/1/reorganize
```

## 🧪 Run Tests

```bash
# All tests
pytest tests/ -v --cov=packages

# Unit tests only
pytest tests/unit/ -v

# Specific test
pytest tests/unit/test_services.py::test_create_file -v
```

## 💻 Local Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Start databases
docker-compose -f infra/docker/docker-compose.yml up -d postgres redis qdrant

# Run API
uvicorn apps.api.main:app --reload

# In another terminal, run tests
pytest tests/ -v
```

## 📁 Key Files

| File | Purpose |
|------|---------|
| `apps/api/main.py` | FastAPI endpoints |
| `packages/core/file_service.py` | File operations |
| `packages/ai/service.py` | AI features |
| `packages/rbac/service.py` | Access control |
| `packages/core/models.py` | Database models |
| `packages/plugins/manager.py` | Plugin system |
| `tests/unit/test_services.py` | Tests |

## 🔧 Environment Variables

```bash
DATABASE_URL=postgresql+asyncpg://hyperaifs:hyperaifs_password@localhost:5432/hyperaifs
REDIS_URL=redis://localhost:6379
QDRANT_URL=http://localhost:6333
OPENAI_API_KEY=sk-...
FILE_STORAGE_DIR=/data/files
```

## 📚 Documentation

| Document | Content |
|----------|---------|
| README.md | Overview & quick start |
| docs/API.md | Complete API reference |
| docs/ARCHITECTURE.md | System design |
| docs/DEPLOYMENT.md | Production deployment |
| docs/PLUGINS.md | Plugin development |

## 🏗️ Project Structure

```
hyperaifs/
├── apps/api/              # FastAPI application
├── packages/
│   ├── core/              # Core services
│   ├── ai/                # AI services
│   ├── rbac/              # Access control
│   └── plugins/           # Plugin system
├── infra/docker/          # Docker Compose
├── tests/                 # Test suite
├── docs/                  # Documentation
└── Dockerfile             # Production image
```

## 🔐 Roles & Permissions

```
Owner:   Read ✓ Write ✓ Delete ✓ Admin ✓
Admin:   Read ✓ Write ✓ Delete ✓ Admin ✗
Editor:  Read ✓ Write ✓ Delete ✓ Admin ✗
Viewer:  Read ✓ Write ✗ Delete ✗ Admin ✗
Guest:   Read ✓ Write ✗ Delete ✗ Admin ✗
```

## 📊 Database Schema

**Tables:**
- `files` - File metadata + embeddings
- `tags` - Semantic tags
- `file_tags` - File-tag associations
- `users` - User accounts
- `projects` - File projects
- `roles` - Role definitions
- `user_roles` - Role assignments
- `audit_log` - Audit trail
- `access_patterns` - Usage analytics

## 🎯 Common Tasks

### Add Custom Tag
```python
await file_service.add_tag(db, file_id=1, tag_name="custom", user_id=1)
```

### Search Semantically
```python
results = await file_service.search_files_semantic(
    db, query="python agents", project_id=1, user_id=1
)
```

### Auto-Tag File
```python
tags = await file_service.auto_tag_file(db, file_id=1, content="...")
```

### Check Permission
```python
can_read = await rbac_service.can_read_file(db, user_id=1, file_id=1)
```

## 🐛 Debugging

```bash
# View API logs
docker logs -f hyperaifs-api

# Database shell
docker exec -it hyperaifs-postgres psql -U hyperaifs -d hyperaifs

# Redis CLI
docker exec -it hyperaifs-redis redis-cli

# API health
curl http://localhost:8000/health
```

## 🚢 Deployment

**Docker:**
```bash
docker build -t hyperaifs:latest .
docker run -p 8000:8000 hyperaifs:latest
```

**Kubernetes:**
```bash
kubectl apply -f infra/k8s/
```

**Cloud:**
See docs/DEPLOYMENT.md for AWS, GCP, Azure instructions

## 💡 Tips

1. Use semantic search instead of tag search
2. Check API docs at /docs endpoint
3. Enable SQL logging for debugging: `export SQL_ECHO=true`
4. Monitor embedding generation costs (OpenAI API)
5. Cache frequently accessed files in Redis
6. Use plugins for custom storage backends
7. Review audit logs regularly

## 🆘 Common Issues

**"Connection refused"**
- Ensure Docker containers are running: `docker-compose ps`

**"Database does not exist"**
- Run database initialization: `await init_db()`

**"OpenAI API error"**
- Check API key: `echo $OPENAI_API_KEY`
- Verify account has credits

**"Permission denied"**
- Check user role: `rbac_service.get_user_roles()`
- Verify resource ownership

**"Slow queries"**
- Check indexes: `SELECT * FROM pg_indexes`
- Monitor cache hits: `redis-cli INFO stats`

## 📞 Getting Help

1. Check docs/ for detailed guides
2. Review comments in source code
3. Run tests to understand expected behavior
4. Check GitHub issues
5. Review API examples in test files

---

**Version:** 0.1.0  
**Last Updated:** 2024-03-08  
**Status:** Production Ready ✅
