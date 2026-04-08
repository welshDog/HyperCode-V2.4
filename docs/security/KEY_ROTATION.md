# API Key Rotation Runbook 🔑

## Overview
This runbook details the zero-downtime API key rotation strategy for HyperCode V2.0 using the Redis-based Key Store.

## Architecture
- **Storage**: Active keys are stored in a Redis Set (`api_keys:active`).
- **Metadata**: Key creation date and labels are stored in Redis Keys (`api_key:{key}:meta`).
- **Validation**: `app.core.auth.verify_api_key` checks the Redis Set first, then falls back to the `API_KEY` env var (legacy).

## Rotation Procedure

### Phase 1: Generate New Key
1.  **Access**: Shell into the `hypercode-core` container or use a management script.
    ```bash
    docker compose exec hypercode-core python
    ```
2.  **Generate**:
    ```python
    from app.services.key_manager import key_manager
    import asyncio
    
    key = asyncio.run(key_manager.generate_key(label="2024-Q1-Rotation"))
    print(f"New Key: {key}")
    ```
3.  **Distribute**: Securely share the `New Key` with consumers (e.g., Coder Agent config, Frontend Env Vars).

### Phase 2: Propagation (Zero Downtime)
1.  Update consumer configurations with the `New Key`.
2.  Restart consumers if necessary (e.g., `docker compose restart coder-agent`).
3.  **Verify**: Ensure consumers are successfully connecting using the new key. Monitor logs for 403 errors.

### Phase 3: Revocation (Deprecation)
1.  Once all consumers are migrated, revoke the old key.
2.  **Identify Old Key**:
    ```python
    keys = asyncio.run(key_manager.list_keys())
    for k in keys:
        print(f"{k.key} - {k.created_at} - {k.label}")
    ```
3.  **Revoke**:
    ```python
    asyncio.run(key_manager.revoke_key("old_key_string"))
    ```

## Emergency Revocation
In case of a key compromise:
1.  Immediately generate a new key and deploy it to critical services.
2.  Revoke the compromised key using the steps above.
3.  Restart `hypercode-core` if the compromised key matches the `API_KEY` env var (Legacy Fallback) to clear it from memory/config (requires updating `.env` to remove/change it).

## Automation
Future improvements will expose these actions via a protected `POST /admin/keys` API endpoint.
