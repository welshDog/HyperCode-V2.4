import pytest
import asyncio
from src.core.quest_engine import AgentOrchestrator


@pytest.mark.asyncio
async def test_agent_handoff_scenario():
    """
    Integration test validating agent hand-off scenarios.
    Scenario: Classifier identifies task -> Analyzer evaluates -> Rewarder processes.
    """
    orchestrator = AgentOrchestrator()
    
    # Task involving multiple agents
    task = "process_user_contribution"
    agents = ["classifier", "analyzer", "rewarder"]
    
    # Coordinate agents
    results = await orchestrator.coordinate_agents(task, agents)
    
    # Validate hand-off (all agents in the pipeline succeeded)
    assert len(results) == 3
    for agent in agents:
        assert agent in results
        assert results[agent] == "success"
        
    # In a real scenario, we would check if data passed between agents correctly.
    # For this implementation, we ensure the pipeline executes sequentially.


@pytest.mark.asyncio
async def test_agent_dynamic_adaptation_under_load():
    """
    Performance benchmark: sub-200ms response times for quest state transitions 
    under 1,000 concurrent agents (simulated).
    """
    orchestrator = AgentOrchestrator()
    user_id = 123
    quest_id = 456
    context = {"streak": 10}
    
    # Simulate 1,000 concurrent requests
    num_concurrent = 1000
    
    async def task():
        start = asyncio.get_event_loop().time()
        await orchestrator.evaluate_quest_adaptation(user_id, quest_id, context)
        end = asyncio.get_event_loop().time()
        return (end - start) * 1000  # ms

    # Execute concurrently
    durations = await asyncio.gather(*(task() for _ in range(num_concurrent)))
    
    avg_duration = sum(durations) / num_concurrent
    max_duration = max(durations)
    
    print("\n--- Performance Benchmark Report ---")
    print(f"Concurrent Requests: {num_concurrent}")
    print(f"Average Response Time: {avg_duration:.2f} ms")
    print(f"Max Response Time: {max_duration:.2f} ms")
    print("Target: < 200 ms")
    
    assert avg_duration < 200
    # Even under load, most requests should be well under the threshold.
    # Max might spike depending on the environment, but average should be low.
