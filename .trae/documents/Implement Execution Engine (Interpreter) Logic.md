# Implementation Plan: Execution Engine (Interpreter)

We will implement the Execution Engine to allow the Core system to execute code snippets. This will serve as the "Interpreter" layer for HyperCode.

## 1. Schemas
- **File**: Create `app/schemas/execution.py`
- **Models**:
    - `ExecutionRequest`: Input schema (`language`, `code`, `env_vars`, `timeout`).
    - `ExecutionResult`: Output schema (`stdout`, `stderr`, `exit_code`, `status`, `duration`).

## 2. Execution Service
- **File**: Create `app/services/execution_service.py`
- **Class**: `ExecutionService`
- **Features**:
    - **Async Execution**: Use `asyncio.create_subprocess_exec` to run commands without blocking the event loop.
    - **Language Support**:
        - `python`: Executes via `python -c`.
        - `shell`: Executes via `bash -c`.
    - **Safety**: Implement configurable timeouts (default 30s) to prevent infinite loops.
    - **Environment**: Allow passing custom environment variables.
    - **Error Handling**: Capture `stderr` and non-zero exit codes.

## 3. Router Implementation
- **File**: Update `app/routers/execution.py`
- **Endpoints**:
    - `POST /execute`: Main endpoint to run code.
    - `GET /health`: Simple health check for the execution subsystem.

## 4. Verification & Testing
- **Integration Test**: Create `tests/test_execution_api.py`.
    - Test successful Python execution (`print("hello")`).
    - Test syntax errors (stderr capture).
    - Test infinite loop handling (timeout).
- **Manual Verification**: Use `curl` to run a snippet.

## Execution Steps
1.  Create `app/schemas/execution.py`.
2.  Implement `app/services/execution_service.py`.
3.  Update `app/routers/execution.py`.
4.  Create and run `tests/test_execution_api.py`.
