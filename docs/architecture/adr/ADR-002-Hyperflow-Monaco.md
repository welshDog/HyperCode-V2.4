# ADR-002: Hyperflow Editor uses Monaco; Broski SSE timeline confirmed

## Context
- The Hyperflow Editor needs a fast, accessible code editing experience with custom tokenization.
- Broski Terminal displays real-time agent activity via SSE.

## Decision
- Choose Monaco Editor for Hyperflow due to mature APIs and Monarch tokenization.
- Wire Ctrl+Enter to POST /execution/execute-hc; show output inline.
- Subscribe Broski to /agents/stream SSE and render timeline with a light metrics overlay (event rate, last event age).

## Status
- Accepted

## Consequences
- Frontend can iterate quickly on language tokens and UX.
- SSE timeline provides immediate feedback and observability during runs.

