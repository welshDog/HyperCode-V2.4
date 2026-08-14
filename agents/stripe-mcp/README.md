# Stripe MCP Server

MCP server exposing Stripe checkout, webhooks, and subscriptions as tools and resources for AI agents.

## Capabilities

### Tools

- `create_checkout(price_id: str, user_id: str)`  
  Create a Stripe Checkout Session for a given price and user. Wraps the existing `create_checkout_session()` logic.

- `handle_webhook_event(payload: str, sig_header: str)`  
  Verify and handle a Stripe webhook event. Wraps the webhook handling logic from `stripe_service.py`.

- `get_subscription(user_id: str)`  
  Return the current subscription status for a user (from local DB or Stripe).

### Resources

- `stripe://subscription/{user_id}`  
  Read-only resource exposing a user's subscription status.

- `stripe://plans`  
  Read-only resource listing available Stripe plans (starter, builder, hyper, pro, elite).

## Architecture

- Runs on `agent-net` alongside other agents.
- Connects to the shared PostgreSQL database (async engine) and Stripe API.
- Uses Docker secrets for Stripe keys and DB credentials.
- Exposes an MCP server over HTTP on port 8100.

## Deployment

See `docker-compose.stripe-mcp.yml` in the repo root for the service definition.
