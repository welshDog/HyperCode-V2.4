# Stripe MCP Server

This doc covers how to run and test the Stripe MCP server, which exposes Stripe checkout, webhooks, and subscriptions as MCP tools and resources.

## Overview

The server provides:

### Tools

- `create_checkout(price_id, user_id)` — Create a Stripe Checkout Session for a given price and user.
- `handle_webhook_event(payload, sig_header)` — Verify and handle a Stripe webhook event.
- `get_subscription(user_id)` — Get a user's subscription status.

### Resources

- `stripe://subscription/{user_id}` — Read-only subscription status resource.
- `stripe://plans` — List of available Stripe plans (starter, builder, hyper, pro, elite).

This follows the Model Context Protocol (MCP) pattern: tools, resources, and prompts exposed over a standard interface.[web:16][web:19][web:25]

## Running the Server

### 1. Ensure secrets exist

You need the following secrets in `secrets/`:

```bash
# From HyperCode-V2.4 root
echo "postgresql://user:pass@postgres:5432/hypercode" > secrets/database_url.txt
echo "sk_live_xxx" > secrets/stripe_secret_key.txt
echo "whsec_xxx" > secrets/stripe_webhook_secret.txt
```

And the following env vars in your `.env` / compose environment:

```env
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_PRICE_STARTER=price_xxx
STRIPE_PRICE_BUILDER=price_xxx
STRIPE_PRICE_HYPER=price_xxx
STRIPE_PRICE_PRO_MONTHLY=price_xxx
STRIPE_PRICE_PRO_YEARLY=price_xxx
STRIPE_PRICE_HYPER_MONTHLY=price_xxx
STRIPE_PRICE_HYPER_YEARLY=price_xxx
STRIPE_SUCCESS_URL=http://localhost:3000/payment-success
STRIPE_CANCEL_URL=http://localhost:3000/pricing
```

Adjust URLs and price IDs to match your Stripe dashboard.

### 2. Start the service

Include the new compose file when starting the stack:

```powershell
docker compose `
  -f docker-compose.yml `
  -f docker-compose.secrets.yml `
  -f docker-compose.stripe-mcp.yml `
  up -d stripe-mcp
```

Or add `stripe-mcp` to your existing `docker compose up -d` command.

### 3. Verify health

```powershell
curl http://localhost:8100/health
```

Expected: `{"status":"ok"}`

### 4. Check MCP discovery

```powershell
curl http://localhost:8100/.well-known/mcp
```

Expected: JSON with `tools` and `resources` matching the definitions in `server.py`.

## Testing Tools

### Create checkout

```powershell
curl -X POST http://localhost:8100/mcp/tools/create_checkout `
  -H "Content-Type: application/json" `
  -d '{"price_id": "starter", "user_id": "123456789012345678"}'
```

Expected: `{"success": true, "checkout_url": "https://checkout.stripe.com/...", ...}`

### Handle webhook event

Use Stripe CLI to forward a test event, or manually POST a signed payload:

```powershell
curl -X POST http://localhost:8100/mcp/tools/handle_webhook_event `
  -H "Content-Type: application/json" `
  -d '{"payload": "{\"id\":\"evt_xxx\",\"type\":\"checkout.session.completed\"}", "sig_header": "t=xxx,v1=xxx"}'
```

Expected: `{"success": true, "event_type": "checkout.session.completed", ...}`

### Get subscription

```powershell
curl -X POST http://localhost:8100/mcp/tools/get_subscription `
  -H "Content-Type: application/json" `
  -d '{"user_id": "123456789012345678"}'
```

Expected: `{"user_id": "123456789012345678", "status": "active" | "none"}`

## Testing Resources

### Subscription resource

```powershell
curl "http://localhost:8100/mcp/resources/stripe://subscription/123456789012345678"
```

### Plans resource

```powershell
curl "http://localhost:8100/mcp/resources/stripe://plans"
```

Expected: `["starter", "builder", "hyper", "pro_monthly", "pro_yearly", ...]`

## Integrating with Agents

To use this from your existing agents:

1. Have the agent call `GET /.well-known/mcp` to discover available tools.
2. When the agent needs to create a checkout or check a subscription, it POSTs to `/mcp/tools/{tool_name}` with the appropriate JSON body.
3. For read-only views, agents can GET the `stripe://...` resource URLs.

Later, you can wire this into MCP clients (Claude Desktop, VS Code, Cursor) by configuring them to point at this server's endpoint.

## Observability

- Logs: `docker logs stripe-mcp`
- Metrics: integrate with Prometheus via `/metrics` in a future iteration.
- Traces: add OpenTelemetry OTLP export to align with HyperCode's existing tracing.

## Security Notes

- The server runs as non-root (`appuser`) following Phase 9 patterns.
- It uses shared secrets for DB and Stripe; ensure these are properly secured and rotated.
- Rate limiting and auth can be added at the API gateway / ingress layer if exposed externally.

## Next Steps

Future iterations can:

- Add OpenTelemetry tracing (OTLP) to match HyperCode core.
- Add a `/metrics` endpoint for Prometheus.
- Wrap this server with an official MCP SDK implementation for broader client compatibility.
- Extend with more resources (e.g., `stripe://customer/{user_id}`, `stripe://payments/{user_id}`).
