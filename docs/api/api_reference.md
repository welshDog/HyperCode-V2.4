# API Reference

> **built with WelshDog + BROski 🚀🌙**

This document describes the core REST API endpoints for HyperCode V2.0.

**Interactive Documentation:**
For real-time testing and schema details, visit the Swagger UI:
👉 **[http://localhost:8000/docs](http://localhost:8000/docs)**

## Base URL
`http://localhost:8000/api/v1`

## Endpoints

### Health Check
**GET** `/health`
- **Description:** Returns the system health status.
- **Response:**
  ```json
  {
    "status": "healthy",
    "version": "2.0.0",
    "services": {
      "database": "up",
      "redis": "up"
    }
  }
  ```

### Agents

#### List Agents
**GET** `/agents`
- **Description:** Retrieves a list of available agents.
- **Response:** `200 OK` - Array of Agent objects.

#### Deploy Agent
**POST** `/agents/{agent_id}/deploy`
- **Description:** Triggers an agent deployment task.
- **Body:**
  ```json
  {
    "task": "string",
    "context": {}
  }
  ```
- **Response:** `202 Accepted` - Task ID.

### Execution

#### Get Execution Status
**GET** `/executions/{execution_id}`
- **Description:** Gets the status and logs of a specific task execution.
- **Response:**
  ```json
  {
    "id": "uuid",
    "status": "running|completed|failed",
    "logs": ["..."]
  }
  ```

## Error Handling
Standard HTTP status codes are used:
- `400`: Bad Request
- `401`: Unauthorized
- `404`: Not Found
- `500`: Internal Server Error

---
> **built with WelshDog + BROski 🚀🌙**
