# HyperAIFS - HyperCode AI File System

> ⚠️ **Working Notes** — `docs/notes/` contains internal documents and historical drafts. For current HyperCode V2.0 setup and architecture, start with [README.md](../../README.md) and [docs/index.md](../index.md).

**Snapshot Notice:** This document describes a separate/older “HyperAIFS” concept and is not the current HyperCode V2.0 stack. For current setup and architecture, start with [README.md](../../README.md) and [docs/index.md](../index.md).

**Doc Tag:** v2.0.0 | **Last Updated:** 2026-03-10

A semantic, AI-driven file management system built on top of traditional storage, optimized for neurodivergent workflows and agent automation.

## 🎯 Overview

HyperAIFS is an intelligent file management system that uses AI embeddings, semantic tagging, and dynamic hierarchy generation to help teams manage millions of files efficiently. Instead of rigid folder hierarchies, files are automatically categorized using LLM embeddings and usage patterns.

**Key Features:**
- 🧠 **Semantic Search**: Find files by meaning, not just keywords
- 🏷️ **Auto-Tagging**: AI-powered automatic file categorization
- 📊 **Dynamic Hierarchy**: Folders reorganize based on access patterns
- 🔐 **RBAC**: Fine-grained role-based access control
- ⚡ **Sub-second Queries**: Optimized for millions of files
- 🔌 **Plugin Architecture**: Extend with custom handlers and AI models

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose (recommended)
- Python 3.10+ (if running locally)
- OpenAI API key (for AI features)

### Deploy with Docker Compose

1. **Clone the repository:**
```bash
git clone https://github.com/hypercode/hyperaifs.git
cd hyperaifs
```

2. **Set environment variables:**
```bash
export OPENAI_API_KEY="your-api-key-here"
```

3. **Start the system:**
```bash
docker-compose -f infra/docker/docker-compose.yml up -d
```

4. **Verify health:**
```bash
curl http://localhost:8000/health
```

The system will be available at:
- **API**: http://localhost:8000
- **Swagger Docs**: http://localhost:8000/docs
- **Postgres**: localhost:5432
- **Redis**: localhost:6379
- **Qdrant**: http://localhost:6333

### Local Development

1. **Install dependencies:**
```bash
pip install -e ".[dev]"
```

2. **Start services locally:**
```bash
docker-compose -f infra/docker/docker-compose.yml up postgres redis qdrant
```

3. **Run the API:**
```bash
uvicorn apps.api.main:app --reload
```

4. **Run tests:**
```bash
pytest tests/ -v
```

## 📚 Core Concepts

### Semantic Tagging
Files are automatically tagged using AI embeddings from their content. Tags represent semantic meaning, not just keywords.

### Dynamic Folders
Virtual folders created from queries like:
```json
{
  "tags": ["python", "ml"],
  "created_after": "2024-01-01",
  "min_accesses": 5
}
```

### Access Patterns
The system tracks which files are accessed together, enabling smart reorganization that matches real workflows.

### RBAC Hierarchy
- **Owner**: Full control including admin capabilities
- **Admin**: Can modify permissions and settings (no global admin)
- **Editor**: Can create, modify, and organize files
- **Viewer**: Read-only access
- **Guest**: Limited read access

## 🔌 API Endpoints

### Files

**Upload File**
```bash
POST /api/files/upload
  ?project_id=1
  
Content-Type: multipart/form-data
Body: {file data}
```

**Get File**
```bash
GET /api/files/{file_id}
```

**List Files**
```bash
GET /api/projects/{project_id}/files
  ?tags=python,ml
  &limit=50
  &offset=0
```

**Semantic Search**
```bash
POST /api/files/search
Body: {
  "query": "python agents for automation",
  "tags": ["python"],
  "limit": 20
}
```

**Delete File**
```bash
DELETE /api/files/{file_id}?hard_delete=false
```

### Tags

**Add Tag to File**
```bash
POST /api/files/{file_id}/tags
Body: {
  "tag_name": "important"
}
```

**Remove Tag from File**
```bash
DELETE /api/files/{file_id}/tags/{tag_id}
```

**List All Tags**
```bash
GET /api/tags
```

### Reorganization

**Trigger Project Reorganization**
```bash
POST /api/projects/{project_id}/reorganize
```

Response:
```json
{
  "clusters_created": 12,
  "total_files_analyzed": 1250,
  "dynamic_folders": [
    {
      "id": 1,
      "name": "Cluster: python + ml",
      "query": {
        "tags": ["python", "ml"],
        "min_accesses": 5
      }
    }
  ]
}
```

## 🏗️ Architecture

### Technology Stack
- **Backend**: FastAPI + SQLAlchemy + Async
- **Database**: PostgreSQL with pgvector
- **Cache**: Redis
- **Vector Search**: Qdrant
- **AI**: OpenAI (embeddings + GPT)
- **Container**: Docker
- **Tests**: pytest
- **CI/CD**: GitHub Actions

### System Components

```
┌─────────────────────────────────────────────────────┐
│                 FastAPI REST API                    │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │File      │  │Tag       │  │RBAC      │         │
│  │Service   │  │Manager   │  │Service   │         │
│  └──────────┘  └──────────┘  └──────────┘         │
│                                                     │
│  ┌────────────────────────────────────┐           │
│  │   AI Service (Embeddings/Tagging)  │           │
│  └────────────────────────────────────┘           │
│                                                     │
│  ┌────────────────────────────────────┐           │
│  │  Reorganization Engine              │           │
│  └────────────────────────────────────┘           │
├─────────────────────────────────────────────────────┤
│  PostgreSQL  │  Redis  │  Qdrant  │  Storage        │
└─────────────────────────────────────────────────────┘
```

### Data Model

**Files**: Core file storage with embeddings and metadata
**Tags**: Semantic tags (auto-generated or manual)
**FileTag**: Association with confidence scores
**DynamicFolder**: Query-based virtual folders
**Users**: User accounts with metadata
**UserRole**: RBAC assignments with resource scoping
**AuditLog**: Complete audit trail
**AccessPattern**: Track usage for reorganization

## 🔐 Security

### Features
- Row-level security via RBAC
- Audit logging for all operations
- Role-based permissions cascade
- Encryption support for sensitive data

### Implement Authentication
The system includes a placeholder authentication system. To implement production authentication:

1. Add JWT token validation in `get_current_user()`
2. Use `python-jose` for token management
3. Implement token refresh logic
4. Add rate limiting

Example:
```python
from jose import JWTError, jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401)
    except JWTError:
        raise HTTPException(status_code=401)
    return await get_user(db, username=username)
```

## 🔌 Plugin System

Extend HyperAIFS with custom plugins:

### Storage Plugin
```python
from packages.plugins.manager import IStoragePlugin

class S3StoragePlugin(IStoragePlugin):
    async def upload(self, file_path: str, content: bytes) -> str:
        # Upload to S3
        pass

    async def download(self, file_path: str) -> bytes:
        # Download from S3
        pass
```

### AI Model Plugin
```python
from packages.plugins.manager import IAIModelPlugin

class CustomAIPlugin(IAIModelPlugin):
    async def tag_file(self, content: str) -> List[Dict]:
        # Custom tagging logic
        pass

    async def generate_embedding(self, text: str) -> List[float]:
        # Custom embedding model
        pass
```

### File Handler Plugin
```python
from packages.plugins.manager import IFileHandlerPlugin

class PDFHandler(IFileHandlerPlugin):
    async def extract_text(self, file_path: str) -> str:
        # Extract text from PDF
        pass

    @property
    def supported_types(self) -> List[str]:
        return ["application/pdf"]
```

Register plugins in `pyproject.toml`:
```toml
[project.entry-points."hyperaifs.plugins"]
s3_storage = "hyperaifs_plugins.s3:S3StoragePlugin"
pdf_handler = "hyperaifs_plugins.pdf:PDFHandler"
```

## 📊 Performance

### Benchmarks
- **File Upload**: ~100ms
- **Semantic Search**: ~200ms (10k files)
- **List Files**: ~50ms
- **Tag Operations**: ~30ms
- **Permission Check**: ~5ms

### Scaling
- Supports 10M+ files
- Sub-second queries via indexing
- Redis caching for hot files
- Batch operations for bulk imports
- Async processing throughout

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=packages --cov-report=html

# Only unit tests
pytest tests/unit/ -v

# Only integration tests
pytest tests/integration/ -v

# Specific test
pytest tests/unit/test_services.py::test_create_file -v
```

## 📝 Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/hyperaifs
SQL_ECHO=false

# Redis
REDIS_URL=redis://localhost:6379

# Qdrant
QDRANT_URL=http://localhost:6333

# OpenAI
OPENAI_API_KEY=sk-...

# Storage
FILE_STORAGE_DIR=/tmp/hyperaifs

# Server
LOG_LEVEL=info
```

## 🚢 Deployment

### Docker
```bash
docker build -t hyperaifs:latest .
docker run -p 8000:8000 hyperaifs:latest
```

### Kubernetes
```bash
kubectl apply -f infra/k8s/
```

See `infra/k8s/` for example manifests.

### Cloud Platforms

**AWS**: Use RDS for PostgreSQL, ElastiCache for Redis, manage Qdrant separately
**GCP**: Cloud SQL, Memorystore, custom VM for Qdrant
**Azure**: Azure Database, Azure Cache, VM for Qdrant

## 📖 Documentation

- [API Reference](docs/API.md)
- [Architecture Guide](docs/ARCHITECTURE.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Plugin Development Guide](docs/PLUGINS.md)

## 🤝 Contributing

1. Create feature branch: `git checkout -b feature/name`
2. Make changes and commit: `git commit -am 'Add feature'`
3. Push to branch: `git push origin feature/name`
4. Create Pull Request

All PRs must:
- Pass linting (black, ruff)
- Include tests
- Update documentation
- Pass CI/CD pipeline

## 📄 License

MIT License - see LICENSE file

## 🆘 Support

- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Email**: support@hypercode.io
- **Docs**: https://hyperaifs.hypercode.io

## 🗺️ Roadmap

- [ ] GraphQL API support
- [ ] Full-text search with Elasticsearch
- [ ] File versioning and history
- [ ] Collaborative features (real-time sync)
- [ ] Mobile apps (iOS/Android)
- [ ] Web UI dashboard
- [ ] Advanced analytics
- [ ] Workflow automation
- [ ] ML-powered recommendations
- [ ] Multi-tenant support

## 🎓 Learn More

For detailed implementation guides and best practices, see the [docs](docs/) directory.

---

Made with ❤️ by HyperCode Team
