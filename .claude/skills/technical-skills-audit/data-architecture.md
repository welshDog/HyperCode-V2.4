# 🗄️ Data Architecture — Redis + PostgreSQL

## Redis Usage Patterns

### Cache Layer
```python
import redis.asyncio as aioredis

r = aioredis.from_url("redis://redis:6379", decode_responses=True)

# Cache agent result for 5 minutes
await r.setex(f"agent:{agent_id}:result", 300, json.dumps(result))

# Retrieve cached result
cached = await r.get(f"agent:{agent_id}:result")
```

### Pub/Sub Channels

| Channel | Publisher | Subscriber |
|---|---|---|
| `hypercode:agents:events` | All agents | Crew Orchestrator |
| `hypercode:healer:events` | Healer Agent | Dashboard |
| `hypercode:tasks:queue` | Mission System | Agents |
| `hypercode:broski:coins` | All services | BROski$ Engine |

### BROski$ Economy Store
```python
# Award BROski$ coins
await r.hincrby(f"user:{user_id}:wallet", "coins", amount)

# Get user balance
balance = await r.hget(f"user:{user_id}:wallet", "coins")

# Leaderboard (sorted set)
await r.zadd("broski:leaderboard", {user_id: coins})
top10 = await r.zrevrange("broski:leaderboard", 0, 9, withscores=True)
```

## PostgreSQL Schema Patterns

### Core Tables

```sql
-- Agent registry
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'idle',
    capabilities JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Task queue
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id),
    payload JSONB NOT NULL,
    priority INTEGER DEFAULT 5,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- BROski$ economy
CREATE TABLE broski_wallets (
    user_id VARCHAR(100) PRIMARY KEY,
    coins BIGINT DEFAULT 0,
    xp BIGINT DEFAULT 0,
    level INTEGER DEFAULT 1,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Async SQLAlchemy Pattern

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

engine = create_async_engine(
    "postgresql+asyncpg://user:pass@postgres:5432/hypercode",
    pool_size=20,
    max_overflow=10
)

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

## Seed Data

```bash
# Run database seed script
python scripts/seed_data.py
```

See `scripts/seed_data.py` for default agent registrations, initial BROski$ allocations,
and example mission data.
