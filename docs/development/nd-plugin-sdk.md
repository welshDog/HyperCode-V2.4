# ND Plugin SDK (MCP Tool Servers)

HyperCode V2.0 plugins are implemented as MCP-compatible tool servers. A plugin exposes:

- `GET /mcp/tools` → tool discovery
- `POST /mcp/execute` → tool execution
- a `manifest.json` describing tools + ND safety metadata

The fastest path is to start from the shipped template: `templates/mcp-plugin-python`.

## Quick Start (Python)

1) Copy the template directory and rename the plugin:

- `templates/mcp-plugin-python/` → `plugins/<your-plugin>/` (or keep it in templates while prototyping)

2) Edit `manifest.json`:

- Set `name`, `version`, `author`
- Fill `nd_metadata` honestly (this is used for safety review + discoverability)
- Add tools under `tools[]`

3) Run the server:

- The template uses FastAPI and serves `/mcp/tools` + `/mcp/execute`

## Manifest Contract

Schema: [nd_plugin_manifest.schema.json](file:///h:/HyperStation%20zone/HyperCode/HyperCode-V2.0/config/nd_plugin_manifest.schema.json)

Required fields:

- `name`: unique plugin name
- `version`: plugin version (SemVer recommended)
- `author`: author or org
- `nd_metadata`: ND safety and accessibility metadata
- `tools[]`: list of tool descriptors

Tool descriptor:

- `name`: namespaced tool name (example: `focus.start`)
- `description`: human-readable purpose
- `parameters`: JSON Schema for the tool parameters (object schema)

## ND Safety Rules (Minimum Bar)

Plugins should be safe to run in high cognitive load conditions:

- Avoid surprise motion, popups, or rapid output bursts
- Provide deterministic outputs for the same inputs when possible
- Prefer short, chunkable results and stable formatting
- Never require a cloud dependency unless explicitly configured by the user

If your plugin changes UI state or emits announcements:

- Respect reduced motion preferences
- Ensure keyboard navigability
- Verify screen reader compatibility for critical flows

## Validate Your Manifest

Run the validator before shipping:

```bash
python scripts/validate_nd_plugin_manifest.py \
  --paths templates/mcp-plugin-python/manifest.json
```

To validate multiple manifests at once:

```bash
python scripts/validate_nd_plugin_manifest.py --paths templates plugins
```

## Registering Plugins (MCP Gateway)

The MCP gateway composes tool servers via docker compose.

- See: `docker-compose.mcp-gateway.yml`
- See: `docs/MCP_GATEWAY_OPERATIONAL_GUIDE.md`

At minimum, the gateway must be able to reach your plugin container, and the plugin must expose:

- `/mcp/tools`
- `/mcp/execute`

## Testing Checklist

- `python scripts/validate_nd_plugin_manifest.py` passes
- `/mcp/tools` lists all tools with correct parameter schemas
- `/mcp/execute` rejects unknown tools safely
- Outputs are concise and chunkable for ND users

