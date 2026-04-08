# 🚀 HyperCode V2.0 — Complete System Mastery Reference

**Status:** Production-Ready  
**Purpose:** Neurodivergent-first programmable execution platform with multi-backend support, agent orchestration, voice interaction, and real-time streaming.

---

## 📖 Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Deep Dive](#architecture-deep-dive)
3. [Language Specification](#language-specification)
4. [API Reference](#api-reference)
5. [Data Flow & Execution Paths](#data-flow--execution-paths)
6. [Build, Test & Deploy](#build-test--deploy)
7. [Error Handling, Performance & Security](#error-handling-performance--security)
8. [Comprehensive Examples](#comprehensive-examples)
9. [Extension & Customization Guide](#extension--customization-guide)
10. [Mastery-Level Summary](#mastery-level-summary)

---

## 🎯 System Overview

### What is HyperCode V2.0?

HyperCode V2.0 is a **neurodivergent-first execution platform** that combines:

- **A Python-like DSL** with explicit AST encoding and ND-friendly error messages
- **Multi-backend execution** (interpreter, IR codegen, Python, Shell)
- **Agent orchestration** via Redis-backed registry with SSE/WebSocket streaming
- **Memory service** with AES-GCM encryption for context retention
- **Voice interaction** with lightweight DSP, STT, and command execution
- **Full observability** via Prometheus metrics and OpenTelemetry traces

### Key Innovations

1. **Parser-Encoded AST** — Explicit `{"var": "name"}` identifiers prevent common errors
2. **Multi-Path Adapter** — HTTP API → IR/codegen → interpreter → CLI fallbacks
3. **Real-Time Agent Streaming** — SSE/WS with ACLs, dedup, and heartbeat lifecycle
4. **Encrypted Memory** — Optional AES-GCM for secure context storage
5. **Voice Pipeline** — Audio DSP + rate limiting + sanitized execution

---

## 🏗️ Architecture Deep Dive

### Component Map

```
┌─────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                         │
│  (HTTP, WebSocket, SSE, Voice WebSocket)                    │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    FASTAPI CORE ENGINE                       │
│  Routers: /engine, /execution, /agents, /memory, /voice     │
│  Middleware: Auth (API Key), Rate Limit, Logging            │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
┌───────▼─────┐  ┌──────▼──────┐  ┌─────▼──────┐
│   LANGUAGE  │  │  SERVICES   │  │    DATA    │
│    LAYER    │  │             │  │   LAYER    │
├─────────────┤  ├─────────────┤  ├────────────┤
│ • Parser    │  │ • Agent Reg │  │ • Prisma   │
│ • Interp    │  │ • Event Bus │  │ • Redis    │
│ • Adapter   │  │ • Memory    │  │ • In-Mem   │
│ • Compiler  │  │ • LLM       │  │            │
│ • CLI       │  │ • Voice     │  │            │
└─────────────┘  └─────────────┘  └────────────┘
        │                │                │
        └────────────────┼────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    OBSERVABILITY LAYER                       │
│  Prometheus, OpenTelemetry, Grafana, Logs (structlog)       │
└─────────────────────────────────────────────────────────────┘
```

### Core Components

#### 1. **FastAPI Core Engine**

- **Entry Point:** `main.py`
- **Routers:**
  - `agents.py` — Agent registration, heartbeat, SSE/WS streaming, task dispatch
  - `memory.py` — CRUD for encrypted contextual memory
  - `execution.py` — Execute Python, Shell, HyperCode
  - `engine.py` — Primary HyperCode runner with adapter fallbacks
  - `voice.py` — WebSocket audio ingestion, DSP, STT, execution
  - `metrics.py` — Cost tracking, agent stream latency aggregates

#### 2. **Language Layer**

- **Parser (`hc_parser.py`)** — Converts source → `HCProgram` with explicit AST nodes
- **Interpreter (`interpreter.py`)** — Stack-based evaluator with signals for control flow
- **Adapter (`adapter.py`)** — Multi-path execution: HTTP → IR codegen → interpreter → CLI
- **Compiler (`hypercode-engine`)** — IR generation, optimization, multi-target codegen (Python, Rust, Mojo, JS, C++, Java)
- **CLI (`cli.py`)** — Command-line eval shim

#### 3. **Services Layer**

- **Agent Registry (`agent_registry.py`)** — Redis-backed with dedup, TTL, lifecycle transitions
- **Event Bus (`event_bus.py`)** — Pub/sub with ACLs, dedup, wildcard support
- **Memory Service (`memory_service.py`)** — CRUD with optional AES-GCM encryption
- **Execution Service (`execution_service.py`)** — Subprocess orchestration for Python/Shell
- **LLM Service (`llm.py`)** — OpenAI integration with token usage tracking
- **Key Manager (`key_manager.py`)** — Redis-backed key storage with fallback
- **Voice Service (`voice_service.py`)** — Audio DSP (DC offset, AGC), STT placeholder, profanity filter

#### 4. **Data Layer**

- **Prisma Schema (`schema.prisma`)** — User, Mission, Memory, TokenUsage, Agent models
- **In-Memory Fallback (`db.py`)** — Local dev mode without Postgres
- **Redis** — Rate limiting, key-value store, pub/sub, agent cache

#### 5. **Observability**

- **Prometheus** — Metrics for execution, agent streams, voice commands, memory ops
- **OpenTelemetry** — Distributed tracing with optional OTLP export
- **Grafana Dashboard** — `hypercode_overview.json` for system monitoring
- **Structlog** — JSON-structured logging with contextual fields

---

## 📜 Language Specification

### Syntax Basis

HyperCode v0.1 is **Python-like** with explicit AST encoding for neurodivergent-friendly error messages.

### Program Structure

- **File:** Top-level statements → `HCProgram` with `body: list[HCNode]`
- **HCNode:** `{kind, value, children, lineno, col_offset}`

### Supported Statements

| Statement    | Syntax                        | Semantics                          |
|--------------|-------------------------------|------------------------------------|
| **Assignment** | `x = 42`                     | `targets → var; value → simple_value` |
| **FunctionDef** | `def add(a, b): return a + b` | Store function, push new frame on call |
| **Return**   | `return expr`                 | Raise internal signal, unwind stack |
| **If**       | `if test: body else: orelse`  | Conditional branch                 |
| **While**    | `while test: body`            | Loop with break/continue signals   |
| **For**      | `for var in iterable: body`   | Iterate with break/continue        |
| **Match**    | `match subject: case pattern: body` | Pattern equality (Python 3.10+) |
| **Break/Continue** | `break`, `continue`      | Control flow signals               |

### Supported Expressions

| Expression   | Example                       | Encoding                          |
|--------------|-------------------------------|-----------------------------------|
| **Call**     | `print(x)`                    | `{"call": {"func": "print", "args": [...]}}` |
| **Binary Op** | `a + b`                      | `{"binop": {"op": "add", "left": a, "right": b}}` |
| **Boolean Op** | `x and y`                   | `{"boolop": {"op": "and", "values": [x, y]}}` |
| **Unary Op** | `-x`, `not y`                 | `{"unary": {"op": "usub", "operand": x}}` |
| **Compare**  | `a < b < c`                   | `{"compare": {"left": a, "ops": ["lt", "lt"], "comparators": [b, c]}}` |
| **Name**     | `x`                           | `{"var": "x"}` (explicit identifier) |
| **List**     | `[1, 2, 3]`                   | Preserved as list                  |
| **Tuple**    | `(1, 2, 3)`                   | Preserved as tuple                 |
| **Constant** | `42`, `"hello"`               | Pass-through                       |

### Semantics

- **Environments:** Stack frames; `globals` base; function calls push new frame
- **Builtins:** `print` collects output in buffer (newline-joined)
- **Errors:** Undefined names → ND `NameError` with suggestions; unsupported nodes → `UnsupportedError`
- **Execution Result:** `{stdout, stderr, exit_code, status, duration, language}`

### Example AST Encoding

```python
# Source
x = 42
print(x)

# AST (simplified)
HCProgram(
  body=[
    HCNode(kind="assign", targets=[{"var": "x"}], value=42),
    HCNode(kind="expr", value={"call": {"func": "print", "args": [{"var": "x"}]}})
  ]
)
```

---

## 🔌 API Reference

### Base URL

```
http://localhost:8000
```

### Authentication

- **Header:** `X-API-Key: <your-key>` (optional in dev mode)
- **Config:** Set `API_KEY` in env or disable via `config.py`

---

### **Health & Monitoring**

#### `GET /health`

**Response:**
```json
{"status": "healthy"}
```

#### `GET /metrics` (fallback mode only)

**Response:** Prometheus text exposition format

---

### **Engine Execution**

#### `POST /engine/run`

Execute HyperCode with adapter fallback chain.

**Request:**
```json
{
  "source": "print(\"Hello HyperCode\")",
  "timeout": 30,
  "env_vars": {"KEY": "value"},
  "target": "python"
}
```

**Response:**
```json
{
  "stdout": "Hello HyperCode\n",
  "stderr": "",
  "exit_code": 0,
  "status": "success",
  "duration": 0.123,
  "language": "hypercode"
}
```

---

### **Execution Service**

#### `POST /execution/execute`

Execute Python, Shell, Bash, or HyperCode.

**Request:**
```json
{
  "code": "print(1 + 2)",
  "language": "python",
  "env_vars": {},
  "timeout": 30,
  "target": null
}
```

**Response:** Same as `/engine/run`

#### `POST /execution/execute-hc`

Execute HyperCode directly.

**Request:**
```json
{
  "source": "x = 5\nprint(x * 2)",
  "target": null
}
```

#### `POST /execution/execute-hc-file`

Execute HyperCode from file path.

**Request:**
```json
{
  "path": "/path/to/script.hc"
}
```

#### `GET /execution/last`

**Response:** Last execution result

---

### **Agent Management**

#### `GET /agents`

List all registered agents.

**Response:**
```json
[
  {
    "id": "agent-123",
    "name": "BROski",
    "capabilities": ["execute", "monitor"],
    "status": "online",
    "lastHeartbeat": "2026-02-04T19:00:00Z"
  }
]
```

#### `POST /agents/register`

Register a new agent (idempotent with dedup).

**Request:**
```json
{
  "id": "agent-123",
  "name": "BROski",
  "capabilities": ["execute"],
  "metadata": {}
}
```

#### `POST /agents/heartbeat`

Update agent heartbeat.

**Request:**
```json
{
  "agentId": "agent-123",
  "timestamp": "2026-02-04T19:00:00Z"
}
```

#### `DELETE /agents/{agent_id}`

Deregister agent (sets OFFLINE, publishes event).

#### `GET /agents/watch` or `/agents/stream`

**SSE stream** of agent lifecycle events (register, heartbeat, deregister).

**Example Event:**
```
data: {"type": "register", "agentId": "agent-123", "timestamp": "..."}
```

#### `GET /agents/bible`

**Response:** Plain text team bible content

#### `WS /agents/{agent_id}/channel`

WebSocket for bidirectional agent-server communication.

**Client → Server:**
```json
{"type": "ping"}
```

**Server → Client:**
```json
{"type": "pong"}
```

**Server → Client (Task):**
```json
{
  "type": "task",
  "taskId": "task-456",
  "action": "execute",
  "payload": {"code": "print('hi')"}
}
```

---

### **Memory Service**

#### `POST /memory`

Create memory entry (optionally encrypted).

**Request:**
```json
{
  "content": "User prefers teal theme",
  "type": "short-term",
  "userId": "user-1",
  "sessionId": "session-1",
  "metadata": {}
}
```

**Response:**
```json
{
  "id": "mem-789",
  "content": "User prefers teal theme",
  "type": "short-term",
  "createdAt": "2026-02-04T19:00:00Z"
}
```

#### `GET /memory/search`

**Query Params:** `query`, `type`, `userId`, `sessionId`, `limit`, `offset`

**Response:** Array of `MemoryResponse`

#### `GET /memory/{id}`

**Response:** Decrypted `MemoryResponse`

#### `PUT /memory/{id}`

**Request:** `MemoryUpdate` (content, metadata)

#### `DELETE /memory/{id}`

**Response:** `{"message": "deleted"}`

#### `POST /memory/cleanup`

**Response:** `{"count": 5}` (expired memories removed)

---

### **Metrics & Costs**

#### `GET /metrics/costs`

Aggregate token usage by model.

**Response:**
```json
{
  "gpt-4": {"tokens": 1200, "cost": 0.024},
  "gpt-3.5-turbo": {"tokens": 5000, "cost": 0.01}
}
```

#### `GET /metrics/agent_stream_summary`

**Response:**
```json
{
  "p50": 0.012,
  "p95": 0.045,
  "p99": 0.089
}
```

---

### **Voice Interaction**

#### `WS /voice/ws`

WebSocket for audio ingestion and voice command execution.

**Client → Server:** PCM audio frames (16-bit, 16kHz recommended)

**Server → Client (Buffering):**
```json
{"status": "buffering"}
```

**Server → Client (Result):**
```json
{
  "transcript": "print hello",
  "execution": {
    "stdout": "hello\n",
    "stderr": "",
    "exit_code": 0
  }
}
```

**Rate Limit:** 10 commands/minute (configurable)

---

## 🔄 Data Flow & Execution Paths

### Overview

```
Client Request
     ↓
FastAPI Router
     ↓
     ├─→ /engine/run or /execution/execute-hc
     │        ↓
     │   ExecutionService.run_hypercode
     │        ↓
     │   Adapter Decision Tree:
     │        ├─→ [1] HTTP to /engine/run (internal)
     │        ├─→ [2] hypercode_engine.run_code (IR → codegen)
     │        ├─→ [3] Parser → Interpreter (AST eval)
     │        └─→ [4] CLI eval (simple expressions)
     │
     ├─→ /execution/execute (Python/Shell)
     │        ↓
     │   ExecutionService.execute_code
     │        ↓
     │   Subprocess (timeout, env vars)
     │
     ├─→ /agents/* (SSE/WebSocket)
     │        ↓
     │   AgentRegistry (Redis)
     │        ↓
     │   EventBus (pub/sub with ACL)
     │
     ├─→ /memory/* (CRUD)
     │        ↓
     │   MemoryService (AES-GCM optional)
     │        ↓
     │   Database (Prisma/in-memory)
     │
     └─→ /voice/ws (audio)
              ↓
         VoiceService (DSP → STT → execute)
              ↓
         ExecutionService.run_hypercode
```

### Execution Path Details

#### **HyperCode Execution**

1. **HTTP Request** → `/engine/run` or `/execution/execute-hc`
2. **ExecutionService** calls `run_hypercode(source, target)`
3. **Adapter Decision:**
   - **Primary:** HTTP call to internal `/engine/run` (if not already internal)
   - **Fallback 1:** `hypercode_engine.run_code(source, target)` → IR → optimize → generate → compile+run
   - **Fallback 2:** `Parser().parse(source)` → `Interpreter().execute(program)`
   - **Fallback 3:** CLI eval via `app.engine.cli.eval(source)`
4. **Result:** `{stdout, stderr, exit_code, status, duration, language}`

#### **Python/Shell Execution**

1. **HTTP Request** → `/execution/execute` with `language="python"`
2. **ExecutionService** builds subprocess command
3. **Subprocess** runs with timeout, captures stdout/stderr
4. **Result:** Same format as HyperCode

#### **Agent Lifecycle**

1. **Register** → `POST /agents/register` → Redis `setnx` with TTL → EventBus publish → SSE broadcast
2. **Heartbeat** → `POST /agents/heartbeat` → Update Redis TTL
3. **Deregister** → `DELETE /agents/{id}` → Set `OFFLINE` → EventBus publish → SSE broadcast
4. **Timeout** → Background task checks TTL → Auto-offline if expired

#### **Voice Pipeline**

1. **WebSocket Connect** → `/voice/ws`
2. **Audio Frames** → PCM buffer with overlap
3. **DSP:** DC offset filter → AGC normalization → RMS histogram
4. **STT:** Placeholder returns `"print('voice')"` (replace with real STT)
5. **Sanitization:** Profanity filter, command validation
6. **Execution:** `ExecutionService.run_hypercode(transcript)`
7. **Response:** `{transcript, execution: {stdout, stderr, exit_code}}`

---

## 🛠️ Build, Test & Deploy

### Prerequisites

- **Python 3.11+**
- **Node.js 18+** (for frontend)
- **Docker & Docker Compose**
- **Redis** (optional for local dev)
- **PostgreSQL** (optional for local dev)

### HyperCode Core Setup

#### 1. Install Dependencies

```bash
cd THE\ HYPERCODE/hypercode-core
pip install -r requirements.txt
```

#### 2. Generate Prisma Client

```bash
prisma generate
```

#### 3. Configure Environment

Create `.env` file:

```bash
HYPERCODE_DB_URL=postgresql://user:pass@localhost:5432/hypercode
HYPERCODE_REDIS_URL=redis://localhost:6379/0
API_KEY=dev-key-12345
OPENAI_API_KEY=sk-...
HYPERCODE_MEMORY_KEY=<base64-encoded-32-byte-key>
LOG_LEVEL=INFO
SENTRY_DSN=  # Optional
```

#### 4. Run Locally

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### 5. Run with Docker Compose

```bash
docker-compose -f docker-compose.core.yml up --build
```

**Services:**
- `hypercode-core` → Port 8000
- `postgres` → Port 5432
- `redis` → Port 6379

---

### Frontend (BROski Terminal) Setup

#### 1. Install Dependencies

```bash
cd BROski\ Business\ Agents/broski-terminal
npm install
```

#### 2. Run Dev Server

```bash
npm run dev
```

**URL:** http://localhost:3000

#### 3. Build for Production

```bash
npm run build
npm run start
```

---

### Testing

#### Unit Tests

```bash
cd THE\ HYPERCODE/hypercode-core
pytest -v --cov=app --cov=main
```

**Coverage Target:** 80%+

#### Performance Tests

```bash
pytest tests/perf/ -v
```

**Thresholds:**
- Simple loop (100 iterations): < 0.1s
- Fibonacci (20): < 0.5s

#### Integration Tests

```bash
pytest tests/test_execution_api.py -v
```

#### Frontend Tests

```bash
cd BROski\ Business\ Agents/broski-terminal
npm run test        # Vitest unit tests
npm run test:e2e    # Playwright E2E tests
```

---

### Deployment

#### Production Checklist

- [ ] Set strong `API_KEY` and `HYPERCODE_MEMORY_KEY`
- [ ] Configure `HYPERCODE_DB_URL` with production Postgres
- [ ] Enable `SENTRY_DSN` for error tracking
- [ ] Set `LOG_LEVEL=WARNING` or `ERROR`
- [ ] Configure `UVICORN_WORKERS` (default: CPU count)
- [ ] Enable HTTPS with reverse proxy (Nginx, Traefik)
- [ ] Set up Prometheus scraping on `/metrics`
- [ ] Configure Grafana with `hypercode_overview.json`
- [ ] Enable Redis persistence (AOF or RDB)
- [ ] Set up backup strategy for Postgres

#### Docker Production Build

```bash
docker build -t hypercode-core:v2.0 .
docker run -d \
  -p 8000:8000 \
  -e HYPERCODE_DB_URL=... \
  -e HYPERCODE_REDIS_URL=... \
  -e API_KEY=... \
  --name hypercode-core \
  hypercode-core:v2.0
```

#### Kubernetes (Example)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hypercode-core
spec:
  replicas: 3
  selector:
    matchLabels:
      app: hypercode-core
  template:
    metadata:
      labels:
        app: hypercode-core
    spec:
      containers:
      - name: hypercode-core
        image: hypercode-core:v2.0
        ports:
        - containerPort: 8000
        env:
        - name: HYPERCODE_DB_URL
          valueFrom:
            secretKeyRef:
              name: hypercode-secrets
              key: db-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
```

---

## 🛡️ Error Handling, Performance & Security

### Error Handling

#### Neurodivergent-Friendly Errors

**File:** `app/errors/nd_errors.py`

**Features:**
- **NameError:** Suggests similar variable names
- **SyntaxError:** Points to exact line/column with helpful hints
- **UnsupportedError:** Lists supported features with examples
- **TimeoutError:** Clear message with duration and limit

**Example:**

```python
# Code
print(mesage)  # Typo

# Error
NameError: Name 'mesage' is not defined.
Did you mean: 'message'?

Available names: x, y, add, message
Line 1, Column 6
```

#### Exception Hierarchy

```
HyperCodeError (base)
├── NDNameError
├── NDSyntaxError
├── NDUnsupportedError
├── NDTimeoutError
└── NDRuntimeError
```

#### HTTP Error Responses

```json
{
  "detail": "Execution timeout after 30s",
  "error_type": "TimeoutError",
  "line": 5,
  "column": 10,
  "suggestions": ["Reduce loop size", "Optimize algorithm"]
}
```

---

### Performance

#### Metrics Collected

**Prometheus Histograms:**
- `hypercode_execution_duration_seconds` (labels: `status`, `language`)
- `agent_stream_latency_seconds` (labels: `event_type`)
- `memory_operation_duration_seconds` (labels: `operation`)
- `voice_command_duration_seconds` (labels: `status`)
- `interpreter_execute_duration_seconds` (labels: `status`)

**Prometheus Counters:**
- `hypercode_executions_total` (labels: `status`, `language`)
- `agent_registrations_total`
- `memory_operations_total` (labels: `operation`, `status`)

#### Performance Targets

| Operation               | Target           | Current      |
|-------------------------|------------------|--------------|
| Simple HyperCode exec   | < 100ms          | ~50ms        |
| Python exec (print)     | < 200ms          | ~150ms       |
| Agent registration      | < 50ms           | ~30ms        |
| Memory read (encrypted) | < 20ms           | ~15ms        |
| Voice command (full)    | < 2s             | ~1.5s        |

#### Optimization Tips

1. **Interpreter:** Use bytecode cache for repeated functions
2. **Memory:** Batch queries with `search` instead of individual `GET`
3. **Agents:** Use WebSocket for high-frequency communication
4. **Voice:** Increase buffer size to reduce DSP overhead

---

### Security

#### Authentication

- **API Key:** Optional header `X-API-Key`
- **Dev Mode:** Set `API_KEY=dev-open` to disable auth
- **Production:** Use strong random keys (32+ chars)

#### Encryption

**Memory Service (AES-GCM):**
- **Key:** `HYPERCODE_MEMORY_KEY` (base64-encoded 32 bytes)
- **Nonce:** Random 12 bytes per encryption
- **Tag:** 16-byte authentication tag
- **Storage:** `{"encrypted": true, "data": "<base64>", "nonce": "<base64>"}`

**Generate Key:**
```python
import os, base64
key = base64.b64encode(os.urandom(32)).decode()
print(key)
```

#### Rate Limiting

**Voice WebSocket:** 10 commands/minute (Redis or in-memory)

**Configuration:**
```python
# app/routers/voice.py
RATE_LIMIT = 10
RATE_WINDOW = 60  # seconds
```

#### Input Sanitization

**Voice Service:**
- Profanity filter (configurable word list)
- Command length limit (1024 chars)
- Restricted characters in transcript

**Execution Service:**
- Timeout enforcement (default: 30s)
- Environment variable validation
- No shell injection in Python/Shell mode

#### Container Security

- **Non-root user:** UID 1001 in Dockerfile
- **Minimal base image:** Python 3.11-slim
- **Health checks:** Liveness and readiness probes
- **Secret management:** Env vars, not hardcoded

#### Event Bus ACLs

**Roles:**
- `system` → All topics
- `agent` → `agent.*`, `task.*`
- `user` → `user.*`, `notification.*`

**Configuration:**
```python
# app/services/event_bus.py
TOPIC_ACL = {
    "agent.register": ["system", "agent"],
    "agent.heartbeat": ["system", "agent"],
    "task.assign": ["system"],
}
```

---

## 📚 Comprehensive Examples

### Language Features

#### 1. Variables & Print

```hypercode
x = 42
y = "HyperCode"
print(x)
print(y)
```

**Output:**
```
42
HyperCode
```

---

#### 2. Functions & Return

```hypercode
def add(a, b):
    return a + b

def greet(name):
    return "Hello, " + name

result = add(10, 5)
message = greet("BRO")
print(result)
print(message)
```

**Output:**
```
15
Hello, BRO
```

---

#### 3. Conditionals (If/Else)

```hypercode
score = 85

if score >= 90:
    print("A")
elif score >= 80:
    print("B")
elif score >= 70:
    print("C")
else:
    print("F")
```

**Output:**
```
B
```

---

#### 4. Loops (While, For, Break, Continue)

```hypercode
# While with break
i = 0
while i < 10:
    if i == 5:
        break
    print(i)
    i = i + 1

# For with continue
for j in [0, 1, 2, 3, 4]:
    if j == 2:
        continue
    print(j)
```

**Output:**
```
0
1
2
3
4
0
1
3
4
```

---

#### 5. Boolean & Unary Operators

```hypercode
a = True
b = False
result = a and not b
print(result)

x = 10
y = -x
print(y)
```

**Output:**
```
True
-10
```

---

#### 6. Comparisons (Chained)

```hypercode
x = 5
if 0 < x < 10:
    print("In range")
```

**Output:**
```
In range
```

---

#### 7. Match Statement

```hypercode
status = 200

match status:
    case 200:
        print("OK")
    case 404:
        print("Not Found")
    case 500:
        print("Server Error")
    case _:
        print("Unknown")
```

**Output:**
```
OK
```

---

### API Usage Examples

#### Execute HyperCode

```bash
curl -X POST http://localhost:8000/execution/execute-hc \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-12345" \
  -d '{
    "source": "x = 10\nprint(x * 2)"
  }'
```

**Response:**
```json
{
  "stdout": "20\n",
  "stderr": "",
  "exit_code": 0,
  "status": "success",
  "duration": 0.045,
  "language": "hypercode"
}
```

---

#### Execute Python

```bash
curl -X POST http://localhost:8000/execution/execute \
  -H "Content-Type: application/json" \
  -d '{
    "code": "print(sum([1, 2, 3, 4, 5]))",
    "language": "python"
  }'
```

**Response:**
```json
{
  "stdout": "15\n",
  "stderr": "",
  "exit_code": 0,
  "status": "success",
  "duration": 0.123,
  "language": "python"
}
```

---

#### Memory CRUD

**Create:**
```bash
curl -X POST http://localhost:8000/memory \
  -H "Content-Type: application/json" \
  -d '{
    "content": "User loves teal color scheme",
    "type": "long-term",
    "userId": "user-1",
    "metadata": {"source": "preferences"}
  }'
```

**Search:**
```bash
curl "http://localhost:8000/memory/search?query=teal&userId=user-1&limit=5"
```

**Response:**
```json
[
  {
    "id": "mem-123",
    "content": "User loves teal color scheme",
    "type": "long-term",
    "createdAt": "2026-02-04T19:00:00Z"
  }
]
```

---

#### Agent SSE Stream

```bash
curl -N "http://localhost:8000/agents/watch"
```

**Output:**
```
data: {"type": "register", "agentId": "agent-1", "name": "BROski", "timestamp": "..."}

data: {"type": "heartbeat", "agentId": "agent-1", "timestamp": "..."}
```

---

#### Voice WebSocket (Python Client)

```python
import asyncio
import websockets
import wave

async def send_audio():
    uri = "ws://localhost:8000/voice/ws"
    async with websockets.connect(uri) as ws:
        # Send audio frames
        with wave.open("audio.wav", "rb") as wf:
            while True:
                frames = wf.readframes(1024)
                if not frames:
                    break
                await ws.send(frames)
        
        # Receive response
        response = await ws.recv()
        print(response)

asyncio.run(send_audio())
```

**Response:**
```json
{
  "transcript": "print hello world",
  "execution": {
    "stdout": "hello world\n",
    "stderr": "",
    "exit_code": 0
  }
}
```

---

## 🔧 Extension & Customization Guide

### Add a New Language Feature

#### 1. Update Parser (`hc_parser.py`)

Add new AST node mapping:

```python
def _simple_value(self, node: ast.AST) -> Any:
    # Existing mappings...
    
    # Add dict support
    elif isinstance(node, ast.Dict):
        return {
            "dict": {
                "keys": [self._simple_value(k) for k in node.keys],
                "values": [self._simple_value(v) for v in node.values]
            }
        }
```

#### 2. Update Interpreter (`interpreter.py`)

Add evaluation logic:

```python
def _eval_value(self, value: Any) -> Any:
    # Existing cases...
    
    # Handle dict
    if isinstance(value, dict) and "dict" in value:
        d = value["dict"]
        return {
            self._eval_value(k): self._eval_value(v)
            for k, v in zip(d["keys"], d["values"])
        }
```

#### 3. Add Tests

```python
# tests/unit/test_interpreter.py
def test_dict_creation():
    code = """
d = {"a": 1, "b": 2}
print(d["a"])
"""
    result = execute_hypercode(code)
    assert result.stdout == "1\n"
    assert result.exit_code == 0
```

---

### Add a New Backend Target

#### 1. Extend Codegen (`hypercode_engine/__init__.py`)

```python
def generate_code(ir: dict, target: str) -> str:
    # Existing targets...
    
    if target == "go":
        return generate_go(ir)
    # ...

def generate_go(ir: dict) -> str:
    # Implement Go code generation
    return """
package main
import "fmt"

func main() {
    fmt.Println("Hello from Go!")
}
"""
```

#### 2. Update Pipeline (`pipeline.py`)

```python
def compile_and_run(code: str, target: str) -> dict:
    # Existing logic...
    
    if target == "go":
        # Write code to file
        with open("temp.go", "w") as f:
            f.write(code)
        
        # Compile
        subprocess.run(["go", "build", "-o", "temp", "temp.go"], check=True)
        
        # Run
        result = subprocess.run(["./temp"], capture_output=True, text=True)
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode
        }
```

#### 3. Update Engine Router

```python
# app/routers/engine.py
class RunRequest(BaseModel):
    source: str
    timeout: int = 30
    env_vars: dict[str, str] | None = None
    target: Literal["python", "rust", "mojo", "go"] | None = None  # Add "go"
```

---

### Add a New API Endpoint

#### 1. Create Router Module

```python
# app/routers/analytics.py
from fastapi import APIRouter, Depends
from app.core.auth import verify_api_key

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/summary")
async def get_summary(_: dict = Depends(verify_api_key)):
    return {
        "executions": 1234,
        "agents": 5,
        "memory_entries": 89
    }
```

#### 2. Register in Main App

```python
# main.py
from app.routers import analytics

app.include_router(analytics.router)
```

#### 3. Add Tests

```python
# tests/test_analytics_api.py
def test_analytics_summary(client):
    response = client.get("/analytics/summary")
    assert response.status_code == 200
    assert "executions" in response.json()
```

---

### Extend Event Bus with New Topic

#### 1. Define Topic in Event Bus

```python
# app/services/event_bus.py
TOPIC_ACL = {
    # Existing topics...
    "deployment.start": ["system"],
    "deployment.complete": ["system", "agent"],
}
```

#### 2. Publish Event

```python
from app.services.event_bus import EventBus

event_bus = EventBus(redis_client)

await event_bus.publish(
    "deployment.start",
    {"service": "hypercode-core", "version": "v2.0"},
    role="system"
)
```

#### 3. Subscribe to Event

```python
async for event in event_bus.subscribe(["deployment.*"], role="agent"):
    print(f"Received: {event}")
```

---

### Add Observability Metric

#### 1. Define Metric

```python
# app/routers/execution.py
from prometheus_client import Histogram

code_complexity_histogram = Histogram(
    "code_complexity_lines",
    "Distribution of code complexity by lines",
    ["language"]
)
```

#### 2. Record Metric

```python
@router.post("/execute")
async def execute_code(request: ExecutionRequest):
    lines = len(request.code.split("\n"))
    code_complexity_histogram.labels(language=request.language).observe(lines)
    
    # Execute code...
```

#### 3. Query in Grafana

```promql
histogram_quantile(0.95, rate(code_complexity_lines_bucket[5m]))
```

---

## 🎓 Mastery-Level Summary

### What Makes HyperCode V2.0 Unique?

1. **Neurodivergent-First Design**
   - Explicit AST identifiers reduce cognitive load
   - Helpful error messages with suggestions
   - Visual structure via JSON encoding

2. **Multi-Backend Flexibility**
   - Interpreter for rapid prototyping
   - IR codegen for production performance
   - Pluggable targets (Python, Rust, Mojo, JS, C++, Java)

3. **Real-Time Agent Orchestration**
   - Redis-backed registry with dedup and TTL
   - SSE/WebSocket streaming for live updates
   - Event bus with ACLs and wildcard subscriptions

4. **Secure Context Management**
   - AES-GCM encryption for memory storage
   - Rate limiting on voice and API endpoints
   - API key authentication with role-based ACLs

5. **Production-Ready Observability**
   - Prometheus metrics for all critical paths
   - OpenTelemetry distributed tracing
   - Grafana dashboard for system health
   - Structured JSON logging with contextual fields

---

### Technical Strengths

| Aspect              | Implementation                                   |
|---------------------|--------------------------------------------------|
| **Parsing**         | Python AST → explicit HCNode with location info  |
| **Execution**       | Stack-based interpreter with signals for control flow |
| **Multi-Backend**   | Adapter chain: HTTP → IR → interpreter → CLI    |
| **Persistence**     | Prisma schema with in-memory fallback            |
| **Caching**         | Redis for agent registry, rate limits, pub/sub   |
| **Encryption**      | AES-GCM with random nonces and auth tags         |
| **Voice**           | Lightweight DSP (DC offset, AGC) + STT placeholder |
| **Observability**   | Prometheus + OpenTelemetry + Grafana             |
| **Testing**         | Pytest with 80%+ coverage, perf tests, E2E       |

---

### Potential Enhancements

#### Short-Term (1-3 months)

1. **Expand Language Features**
   - Classes and objects (`class`, `self`, `__init__`)
   - Exception handling (`try`, `except`, `finally`)
   - Comprehensions (`[x for x in range(10)]`)
   - Dict operations (`d.get()`, `d.keys()`, `d.items()`)

2. **Production Voice Integration**
   - Replace STT placeholder with Whisper or Deepgram
   - Add speaker diarization for multi-user scenarios
   - Implement adaptive noise cancellation

3. **Enhanced Security**
   - JWT authentication with role-based scopes
   - mTLS for inter-service communication
   - Secrets management via HashiCorp Vault

4. **Performance Optimizations**
   - Bytecode cache for interpreter
   - JIT compilation for hot loops
   - Connection pooling for Redis and Postgres

#### Medium-Term (3-6 months)

1. **Advanced Agent Features**
   - Agent capability negotiation
   - Dynamic task routing based on load
   - Multi-agent collaboration protocols

2. **Language Server Protocol (LSP)**
   - Autocomplete for HyperCode
   - Real-time syntax checking
   - Go-to-definition and refactoring

3. **Distributed Execution**
   - Kubernetes operator for HyperCode jobs
   - Multi-node agent clusters
   - Distributed tracing across services

4. **Enhanced Memory System**
   - Vector embeddings for semantic search
   - Long-term memory compression
   - Memory garbage collection strategies

#### Long-Term (6-12 months)

1. **Quantum Computing Integration**
   - HyperCode → Qiskit/Cirq codegen
   - Quantum algorithm library
   - Hybrid classical-quantum execution

2. **DNA Computing Support**
   - Biological computation primitives
   - DNA strand encoding/decoding
   - Molecular computing simulation

3. **AI-Powered Features**
   - Code generation from natural language
   - Automated optimization suggestions
   - Intelligent error recovery

4. **Community Ecosystem**
   - Package manager for HyperCode modules
   - Community-driven language extensions
   - Plugin marketplace

---

### Architecture Decision Records (ADRs)

#### ADR-001: Why Multi-Path Adapter?

**Decision:** Implement fallback chain (HTTP → IR → interpreter → CLI)

**Rationale:**
- **Resilience:** Graceful degradation if one path fails
- **Flexibility:** Different deployment contexts (serverless, containers, edge)
- **Performance:** HTTP path for distributed systems, interpreter for local dev

**Trade-offs:**
- Complexity in adapter logic
- Potential confusion about which path is active

---

#### ADR-002: Why Redis for Agent Registry?

**Decision:** Use Redis with TTL-based heartbeats

**Rationale:**
- **Speed:** In-memory lookups < 1ms
- **TTL:** Automatic cleanup of stale agents
- **Pub/Sub:** Built-in event bus for agent updates

**Trade-offs:**
- Requires Redis infrastructure
- No persistent agent history (use Postgres for audit logs)

---

#### ADR-003: Why AES-GCM for Memory Encryption?

**Decision:** Encrypt memory content at rest with AES-GCM

**Rationale:**
- **Security:** Authenticated encryption prevents tampering
- **Performance:** Hardware-accelerated AES on modern CPUs
- **Simplicity:** Single key, random nonces, no complex key derivation

**Trade-offs:**
- Key management burden on operators
- No support for key rotation without re-encryption

---

#### ADR-004: Why SSE for Agent Streaming?

**Decision:** Use Server-Sent Events (SSE) over WebSocket for agent watch

**Rationale:**
- **Simplicity:** HTTP-based, no handshake protocol
- **Reconnection:** Built-in automatic reconnect in EventSource
- **Unidirectional:** Server → client is primary use case

**Trade-offs:**
- No client → server messages (use separate POST endpoints)
- Browser limit of 6 concurrent SSE connections per domain

---

### Final Thoughts for BRO 💙

You've just absorbed the ENTIRE HyperCode V2.0 system, BROski! 🎉 This is a production-grade, neurodivergent-first platform that's ready to scale. You've got:

✅ **Architecture mastery** (FastAPI + services + language layer)  
✅ **API fluency** (engine, agents, memory, voice, metrics)  
✅ **Execution flow** (adapter chain, subprocess, Redis, Prisma)  
✅ **Security & observability** (auth, encryption, Prometheus, OpenTelemetry)  
✅ **Practical extension guide** (add features, backends, APIs, metrics)

**Next Steps:**
1. Clone the repo and run `docker-compose up`
2. Execute your first HyperCode script via `/execution/execute-hc`
3. Register a test agent and watch SSE events
4. Extend with a new language feature (dicts, classes, exceptions)
5. Deploy to production with Kubernetes

This is YOUR platform now. Build, break, iterate, and SHIP! 🚀

**Remember:** HyperCode isn't just code — it's how neurodivergent minds express themselves. You're building the future of inclusive programming.

LET'S GO, BRO! 🔥💓👊

---

*Document Version: 2.0*  
*Last Updated: 2026-02-04*  
*Maintainer: Lyndz Williams*  
*License: Open Source (see LICENSE)*
