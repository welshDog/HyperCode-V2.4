# Repair Plan: WebSocket 404 & Core Security 🛠️

We will fix the critical communication breakdown between agents and the core, and then secure the exposed API.

## 1. Fix WebSocket 404 (Top Priority)
The code analysis reveals the WebSocket route is correctly defined in `agents.py` (`@router.websocket("/{agent_id}/channel")`) and included in `main.py` with prefix `/agents`.
**The Issue:** The 404 error `ws://hypercode-core:8000/agents/...` likely stems from a mismatch in how `uvicorn` or the router handles the trailing slash or the prefix mapping for WebSockets.
**The Fix:**
- Verify the router prefix logic.
- Add a specific test case for the WebSocket connection in `tests/unit/test_agents.py` to reproduce the failure locally.
- *Hypothesis*: The issue might be related to how FastAPI handles WebSocket routing within `APIRouter` prefixes or a network configuration issue in Docker (less likely given HTTP works). We will consolidate the WebSocket route definition.

## 2. Implement API Key Authentication (Security)
**The Issue:** All endpoints are public.
**The Fix:**
- Create `app/core/auth.py` to handle API Key validation.
- Define `API_KEY` in `app/core/config.py` (read from env).
- Apply `Depends(verify_api_key)` to critical endpoints in `app/routers/agents.py`:
    - `DELETE /{agent_id}`
    - `POST /register`
    - `POST /heartbeat`
    - `WEBSOCKET /{agent_id}/channel` (Need to handle Auth in handshake).

## 3. Execution Steps
1.  **Reproduction**: Create a test in `tests/unit/test_agents.py` that attempts a WebSocket connection.
2.  **Fix**: Adjust `app/routers/agents.py` to ensure the WebSocket route is correctly registered.
3.  **Secure**: Add the `verify_api_key` dependency to the router.
4.  **Verify**: Run the new tests to confirm 200 OK (Auth) and 101 Switching Protocols (WebSocket).

**Outcome**: Agents will reconnect, and the API will be secured against unauthorized access.
