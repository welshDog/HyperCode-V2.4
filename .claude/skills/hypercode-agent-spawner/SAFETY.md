# Agent Safety Limits

## Safety levels

| Level | Can exec shell | Can write files | Can call external APIs | Auto-approve |
|-------|---------------|-----------------|----------------------|-------------|
| strict | No | Read-only | No | No |
| moderate | Yes (sandbox) | Yes (scoped) | Yes (allowlist) | No |
| open | Yes | Yes | Yes | Yes |

## Guardian enforcement

All agent actions pass through Guardian before execution.
Guardian publishes block events to: `hypercode:guardian:blocks`

## Default for new agents: `moderate`
