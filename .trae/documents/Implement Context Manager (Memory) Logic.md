# Implementation Plan: Context Manager (Memory) Logic

We will implement the complete Context Manager logic as requested, moving from the current placeholder to a fully functional memory management system.

## 1. Database Schema Update (Prisma)
- **File**: `prisma/schema.prisma`
- **Changes**:
    - Enhance `Memory` model with:
        - `userId` (String, optional)
        - `sessionId` (String, optional)
        - `metadata` (Json, for complex data)
        - `keywords` (String[], for search)
        - `updatedAt` (DateTime)
        - `expiresAt` (DateTime, for cleanup)
    - Add database indexes for efficient retrieval: `@@index([type])`, `@@index([userId])`, `@@index([sessionId])`.
- **Action**: Run `prisma generate` and `prisma db push` to apply changes.

## 2. Pydantic Schemas
- **File**: Create `app/schemas/memory.py`
- **Models**:
    - `MemoryCreate`: Validation for creating memories.
    - `MemoryUpdate`: Validation for updates.
    - `MemoryResponse`: Output schema including system-generated fields.
    - `MemorySearch`: Search filters (keywords, time range, type).

## 3. Memory Service Implementation
- **File**: Create `app/services/memory_service.py`
- **Class**: `MemoryService`
- **Features**:
    - **CRUD**: `create_memory`, `get_memory`, `update_memory`, `delete_memory`.
    - **Search**: `search_memories` with filtering by timestamp, user, session, and keyword matching.
    - **Cleanup**: `cleanup_expired_memories` to remove records past `expiresAt`.
    - **Thread Safety**: Inherently handled via async DB operations and Postgres transactions.
    - **Serialization**: Automatic JSON serialization for `metadata` via Pydantic/Prisma.
    - **Logging**: Integrated structured logging for all operations.

## 4. API Router Implementation
- **File**: Update `app/routers/memory.py`
- **Endpoints**:
    - `POST /`: Create context/memory.
    - `GET /`: Search memories (query params).
    - `GET /{memory_id}`: Retrieve specific memory.
    - `PUT /{memory_id}`: Update memory.
    - `DELETE /{memory_id}`: Delete memory.
    - `POST /cleanup`: Trigger garbage collection (admin/system task).

## 5. Verification & Testing
- **Integration Test**: Create `tests/test_memory_integration.py` to verify the full flow (DB -> Service -> API).
- **Manual Verification**: Use `curl` to create, search, and retrieve memories via the running container.

## Execution Steps
1.  Update `prisma/schema.prisma`.
2.  Generate and push DB schema.
3.  Create Pydantic schemas.
4.  Implement `MemoryService`.
5.  Update `MemoryRouter`.
6.  Run verification tests.
