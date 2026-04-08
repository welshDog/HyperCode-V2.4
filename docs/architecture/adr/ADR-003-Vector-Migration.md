
# ADR-003: Vector Database Migration Strategy

## Status
Proposed

## Context
HyperCode's current memory system uses an in-app `numpy` implementation for vector similarity search. While this is efficient for prototypes and small-scale deployments (<10k vectors), it faces significant limitations at scale:
- **Memory Usage**: All vectors must be loaded into memory or fetched from DB and parsed, which is inefficient.
- **Latency**: Linear scan O(N) complexity becomes unacceptable as N grows >100k.
- **Concurrency**: Python's GIL limits parallel search throughput in the API server.

We need a strategy to migrate to a dedicated Vector Database solution to support >100k vectors with sub-100ms latency.

## Decision
We will evaluate **pgvector** (PostgreSQL extension) and **Redis Stack** (RediSearch) as the primary candidates.

### Candidate 1: pgvector (PostgreSQL)
- **Pros**:
  - Single source of truth (keep metadata and vectors together).
  - ACID compliance.
  - No new infrastructure if using Postgres.
  - SQL interface is familiar.
- **Cons**:
  - Slightly higher latency than in-memory Redis.
  - Scaling requires scaling the primary DB or read replicas.

### Candidate 2: Redis Stack (RediSearch + Vector Similarity)
- **Pros**:
  - Extremely low latency (in-memory).
  - We already use Redis for caching/queues.
  - Supports efficient pre-filtering.
- **Cons**:
  - RAM expensive (vectors stored in RAM).
  - Data persistence/durability is less robust than Postgres (RDB/AOF).
  - "Split brain" data if metadata is in Postgres and vectors in Redis.

## Proposed Strategy

### Phase 1: Benchmark (Current)
- Establish baseline latency with `numpy` implementation.
- Identify "breaking point" (N vectors where latency > 100ms).

### Phase 2: Hybrid / Dual-Write
- Implement a `VectorStore` abstraction interface.
- Update `MemoryService` to write to both Postgres (JSON) and the chosen Vector Store.
- Add a feature flag `ENABLE_VECTOR_DB_SEARCH`.

### Phase 3: Migration
- Run a background job to backfill existing memories into the Vector Store.
- **pgvector path**:
  - `ALTER TABLE "Memory" ADD COLUMN "embedding_vector" vector(1536);`
  - `UPDATE "Memory" SET "embedding_vector" = ...`
- **Redis path**:
  - Iterate all memories and `FT.ADD` to Redis index.

### Phase 4: Cutover
- Enable `ENABLE_VECTOR_DB_SEARCH`.
- Monitor latency and error rates.
- Deprecate `numpy` search path.

## Recommendation
**Start with pgvector**. 
Since we already store memories in Postgres, adding `pgvector` keeps the architecture simple (Single System of Record). Redis Stack can be introduced later as a caching layer for "hot" memories if extreme low latency is needed.

## Action Items
1. Enable `pgvector` extension in production Postgres.
2. Update Prisma schema to support `vector` type (requires raw SQL or unsupported type handling).
3. Create a migration script for existing data.
