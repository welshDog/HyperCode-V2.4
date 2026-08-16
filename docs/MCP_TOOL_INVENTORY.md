# MCP Tool Inventory

> Source of truth for every MCP-style tool currently in the HyperCode-V2.4
> ecosystem: what it does, whether it mutates state, whether it requires
> auth, and how reachable it actually is today. Originally written
> 2026-08-15; the reachability claims for all three servers were wrong at
> least once and corrected 2026-08-16 against the actual compose files
> (see each server's own note) — a reminder that this doc needs
> re-verifying against source whenever a compose file changes, not just
> trusted from its own history.

## stripe-mcp

**Reachability:** internal-only, and more isolated than that — verified
2026-08-16 that `docker-compose.stripe-mcp.yml` has **no** `ports:` or
`expose:` block at all (corrected; this doc originally, wrongly, said
`127.0.0.1:8100`). Only reachable from sibling containers on
`agent-net`/`data-net`, not published to the host loopback. **Auth:**
required on every route except `/health` — `Authorization: Bearer
<token>` checked against `STRIPE_MCP_AUTH_TOKEN`, `hmac.compare_digest`,
fails closed.

| Tool / Resource | Type | Description |
|---|---|---|
| `create_checkout(price_id, user_id)` | write | Creates a real Stripe Checkout Session for a subscription price |
| `handle_webhook_event(payload, sig_header)` | write | Verifies a Stripe webhook signature and reports the event type/id (does not yet award entitlements — see server.py's own note) |
| `get_subscription(user_id)` | read-only | Returns a user's subscription status |
| `stripe://subscription/{user_id}` (resource) | read-only | Same data as `get_subscription`, resource-addressable |
| `stripe://plans` (resource) | read-only | Lists available Stripe price IDs |

## broski-economy-mcp

**Reachability:** internal-only, same as stripe-mcp — no `ports:`/`expose:`
block in `docker-compose.broski-economy-mcp.yml`, reachable only from
sibling containers, not the host. **Auth:** required on every route except
`/health` — same mechanism, `BROSKI_ECONOMY_MCP_AUTH_TOKEN`.

| Tool / Resource | Type | Description |
|---|---|---|
| `award_tokens(discord_id, amount, reason)` | write | Mints BROski$ via the `award_tokens()` SQL function (SECURITY DEFINER) |
| `spend_tokens(discord_id, amount, item_slug)` | write | Debits BROski$ via `spend_tokens()` (SECURITY DEFINER) |
| `get_balance(discord_id)` | read-only | Current token balance |
| `broski://balance/{discord_id}` (resource) | read-only | Same as `get_balance`, resource-addressable |
| `broski://transactions/{discord_id}?limit=N` (resource) | read-only | Recent transaction history |

## mcp-rest-adapter

**Reachability:** internal-only, but actually the *least* isolated of
the three — `docker-compose.agents.yml` gives it both `expose: "8821"`
and a loopback-only `ports: 127.0.0.1:8821:8821` binding, so unlike
stripe-mcp/broski-economy-mcp (network-only, no `ports:`/`expose:` at
all — see their entries above) this one IS reachable from the Docker
host, not just from sibling containers. (This paragraph has now been
corrected twice: first wrongly claimed no `ports:` mapping existed at
all, then wrongly claimed parity with the other two once that was
fixed — both against the actual compose file, verified 2026-08-16.)
**Auth:** required on `/tools/discover` and `/tools/call` (`/health`
stays open) — same mechanism as the other two,
`MCP_REST_ADAPTER_AUTH_TOKEN`. Closed 2026-08-16, same session as the
other two — was the "Known Gap" this doc originally shipped with.

A thin REST shim in front of the generic third-party `docker/mcp-gateway`
(`github`, `postgres`, `filesystem` servers) plus two local fallback tools.

| Tool | Type | Description |
|---|---|---|
| `filesystem:list_directory(path)` | read-only | Lists a directory, sandboxed to a `:ro` bind-mounted `/workspace` |
| `filesystem:read_file` / `read_text_file(path)` | read-only | Reads a text file, sandboxed to `/workspace`, 1MB cap |
| `github:list_repos(owner)` | read-only | Adapter-local fallback; lists repos for a GitHub org/user |
| `github:*` (dynamic, via upstream gateway) | read-only (typically) | Real GitHub MCP server tools (e.g. `search_repositories`), proxied live via `tools/list` — not enumerable statically, whatever the gateway's `github` server currently exposes |
| `postgres:<action>` (dynamic passthrough) | **unknown — still unconstrained, see below** | Any `action` string is passed straight through to the upstream `postgres` MCP server with no allow-list on this adapter's side |

`GET /tools/discover` aggregates all of the above (upstream `tools/list`
plus the two local fallbacks) into one list. `POST /tools/call` is the
single invocation endpoint for all of them.

## Known Gap — RESOLVED 2026-08-16

`mcp-rest-adapter` had zero inbound authentication on `/tools/discover` and
`/tools/call` when this doc was first written (2026-08-15) — found while
verifying the inventory, not assumed. Closed the same shared-secret
Bearer-token pattern already proven on the other two servers;
`mcp-rest-adapter`'s auth row above reflects the fix.

Still true and unresolved: the `postgres:<action>` passthrough remains
unconstrained — the auth fix controls *who* can call it, not *what* it's
allowed to do. Its actual write capability depends entirely on what the
upstream gateway's `postgres` MCP server permits, which lives inside the
third-party `docker/mcp-gateway` image and hasn't been audited.

## Safe-to-Expose-Later Classification

None of the above should be exposed externally without the write-path
review each one implies:

- **Read-only, low risk if ever exposed:** `get_subscription`,
  `stripe://subscription`, `stripe://plans`, `get_balance`,
  `broski://balance`, `broski://transactions`, `filesystem:list_directory`,
  `filesystem:read_file`, `github:list_repos`, `github:*` (assuming the
  upstream server's own tools stay read-only).
- **Write, needs its own scoped review before ever going external:**
  `create_checkout` (creates real Stripe sessions), `handle_webhook_event`
  (Stripe signature verification — also gated by `STRIPE_WEBHOOK_SECRET`,
  a second independent secret), `award_tokens` / `spend_tokens` (the two
  highest-stakes tools in this whole inventory — direct token minting/debit),
  `postgres:<action>` (unconstrained — must not go external until the
  passthrough is scoped to specific safe actions, if ever).
