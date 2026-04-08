import httpx
import time
import json
import yaml
from typing import Any
from .models import TestScenario, TestCase, TestResult, ScenarioResult
from .evaluator import Evaluator

class TestRunner:
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.evaluator = Evaluator()

    async def run_scenario(self, scenario: TestScenario) -> ScenarioResult:
        results = []
        passed_count = 0
        failed_count = 0
        start_time = time.time()

        print(f"Running Scenario: {scenario.name} ({len(scenario.cases)} cases)")

        async with httpx.AsyncClient(timeout=60.0) as client:
            for case in scenario.cases:
                print(f"  Executing Case: {case.name} [{case.agent}]")
                case_start = time.time()
                try:
                    # Construct URL based on agent and endpoint
                    # If endpoint is absolute, use it. Otherwise, assume orchestrator routing
                    # or direct agent access if we had a service registry.
                    # For now, we'll route everything through orchestrator or use specific port mapping convention
                    # But simpler to assume orchestrator acts as gateway or use localhost ports
                    
                    # Port mapping convention from docker-compose (simplified assumption)
                    # Core: 8000, Orchestrator: 8080, Agents: 8001-80xx
                    # Let's try to use the orchestrator as the main entry point if possible
                    # Or map agent names to ports
                    
                    url = self._resolve_url(case)
                    
                    response = await client.request(
                        method=case.method,
                        url=url,
                        json=case.payload,
                        headers=case.headers,
                        timeout=case.timeout
                    )
                    
                    duration = (time.time() - case_start) * 1000
                    
                    success, score, errors = self.evaluator.evaluate(response, case.expected_results)
                    
                    result = TestResult(
                        case_id=case.id,
                        scenario_id=scenario.id,
                        success=success,
                        score=score,
                        duration_ms=duration,
                        response_data=self._safe_json(response),
                        errors=errors
                    )
                    
                except Exception as e:
                    duration = (time.time() - case_start) * 1000
                    result = TestResult(
                        case_id=case.id,
                        scenario_id=scenario.id,
                        success=False,
                        score=0.0,
                        duration_ms=duration,
                        response_data=None,
                        errors=[str(e)]
                    )

                results.append(result)
                if result.success:
                    passed_count += 1
                    print(f"    ✅ PASSED ({result.duration_ms:.2f}ms)")
                else:
                    failed_count += 1
                    print(f"    ❌ FAILED: {result.errors}")

        total_duration = (time.time() - start_time) * 1000
        overall_score = sum(r.score for r in results) / len(results) if results else 0

        return ScenarioResult(
            scenario_id=scenario.id,
            total_cases=len(scenario.cases),
            passed_cases=passed_count,
            failed_cases=failed_count,
            total_duration_ms=total_duration,
            results=results,
            overall_score=overall_score
        )

    def _resolve_url(self, case: TestCase) -> str:
        # Simple port mapping for local testing
        # In a real env, this might come from env vars or service discovery
        
        # If the case.endpoint is a full URL, use it
        if case.endpoint.startswith("http"):
            return case.endpoint
            
        # Otherwise, construct it against the orchestrator
        return f"{self.base_url}{case.endpoint}"

    def _safe_json(self, response: httpx.Response) -> Any:
        try:
            return response.json()
        except:
            return response.text

    @staticmethod
    def load_scenario(file_path: str) -> TestScenario:
        with open(file_path, 'r') as f:
            if file_path.endswith('.json'):
                data = json.load(f)
            elif file_path.endswith('.yaml') or file_path.endswith('.yml'):
                data = yaml.safe_load(f)
            else:
                raise ValueError("Unsupported file format")
        return TestScenario(**data)

if __name__ == "__main__":
    # Quick test
    pass
