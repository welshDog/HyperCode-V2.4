# Mission API

Base URL: http://localhost:8000

Authentication: Bearer JWT with scopes
- mission:write
- mission:read
- mission:assign

Dev Token Example
- Header: {"alg":"none"}
- Body: {"scopes":"mission:write mission:read mission:assign"}
- Token: eyJhbGciOiJub25lIn0.eyJzY29wZXMiOiJtaXNzaW9uOndyaXRlIG1pc3Npb246cmVhZCBtaXNzaW9uOmFzc2lnbiJ9.

## Endpoints

### Create Mission
- Method: POST
- Path: /orchestrator/mission
- Scope: mission:write
- Request:
  {
    "title": "Strategist Demo: Checkout",
    "priority": 50,
    "payload": {
      "requirements": { "capabilities": ["frontend","backend","qa"] },
      "objectives": "Implement checkout",
      "constraints": "Use existing API"
    }
  }
- Response: MissionStatus

### Assign Next
- Method: POST
- Path: /orchestrator/assign
- Scope: mission:assign
- Response: MissionStatus | 204 No Content

### Start
- Method: POST
- Path: /orchestrator/{mission_id}/start
- Scope: mission:write
- Response: MissionStatus

### Verify
- Method: POST
- Path: /orchestrator/{mission_id}/verify
- Scope: mission:write
- Response: MissionStatus

### Complete
- Method: POST
- Path: /orchestrator/{mission_id}/complete
- Scope: mission:write
- Response: MissionStatus

### Status
- Method: GET
- Path: /orchestrator/{mission_id}
- Scope: mission:read
- Response: MissionStatus

## Models

MissionRequest
- title: string
- priority: number (0–100)
- payload: object
- dependencies: string[] | null

MissionStatus
- id: string
- title: string
- state: queued | assigned | executing | verifying | completed | failed | escalated | deferred
- priority: number
- agent_id: string | null
- created_at: ISO datetime
- updated_at: ISO datetime

## Notes
- Assign returns 204 when no queued missions or no suitable agents
- State transitions are persisted and may emit events to mission.events
- Health: GET /health returns {"status":"healthy"}
