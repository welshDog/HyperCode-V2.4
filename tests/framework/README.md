# Multi-Agent Testing Framework (MATF)

MATF is a comprehensive testing suite designed to evaluate the performance, reliability, and accuracy of the HyperCode Agent Swarm.

## Architecture

The framework consists of the following components:

- **Runner (`runner.py`)**: Executes test scenarios against the running agent swarm.
- **Models (`models.py`)**: Defines the structure of Test Scenarios, Test Cases, and Results using Pydantic.
- **Evaluator (`evaluator.py`)**: Logic to judge whether a test case passed or failed based on defined criteria.
- **Scenarios (`scenarios/`)**: JSON or YAML files defining the tests.

## Creating Test Scenarios

Scenarios are defined in JSON or YAML. A scenario consists of multiple test cases.

### Example Scenario (`scenarios/example.json`)

```json
{
  "id": "smoke_test",
  "name": "Smoke Test",
  "description": "Basic health check",
  "cases": [
    {
      "id": "health_check",
      "name": "Check Health",
      "agent": "orchestrator",
      "endpoint": "/health",
      "method": "GET",
      "payload": {},
      "expected_results": [
        {
          "method": "status_code",
          "value": 200
        }
      ]
    }
  ]
}
```

### Evaluation Methods

- `status_code`: Checks HTTP status code.
- `exact_match`: Checks if response body exactly matches value.
- `contains`: Checks if response string contains value.
- `regex`: Checks if response matches regex pattern.
- `json_schema`: Validates response against a JSON schema (supports arrays and objects).
- `llm_eval`: (Future) Use an LLM to grade the response quality.

## Running Tests

### Method 1: Using Docker (Recommended)

Since the agents run on an internal Docker network, the easiest way to run tests is using the provided Docker Compose configuration which creates a test runner container attached to the correct networks.

1. Ensure the main stack is running:
   ```bash
   docker compose up -d
   ```

2. Run the tests:
   ```bash
   docker compose -f tests/docker-compose.test.yml up
   ```
   This will build a temporary runner container, install dependencies, and execute all scenarios found in `tests/framework/scenarios/`.

### Method 2: Local Python (If ports are exposed)

If you have exposed the Orchestrator port (8080) to your localhost:

1. Install dependencies:
   ```bash
   pip install httpx pydantic pyyaml jsonschema
   ```

2. Run the runner:
   ```bash
   python tests/run_tests.py
   ```

## Adding New Tests

1. Create a new file in `tests/framework/scenarios/` (e.g., `agent_eval.json`).
2. Define your test cases targeting specific agents or workflows.
3. Run the runner.

## Future Improvements

- **LLM Evaluation**: Integrate OpenAI/PERPLEXITY to judge complex code generation tasks.
- **Performance Benchmarking**: Track latency trends over time.
- **Stress Testing**: Scenarios that spawn concurrent requests.
