import unittest
import os
import sys
import asyncio
from unittest.mock import MagicMock, AsyncMock

# Ensure the parent directory is in the path to import the agent module
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

# Mock imports that might fail or need mocking
sys.modules['redis.asyncio'] = MagicMock()
sys.modules['PERPLEXITY'] = MagicMock()

from agent import ProjectStrategist
from base_agent import AgentConfig, TaskRequest

class TestProjectStrategist(unittest.TestCase):

    def setUp(self):
        """
        Setup common test fixtures.
        """
        os.environ["AGENT_NAME"] = "Project Strategist"
        os.environ["AGENT_PORT"] = "8001"
        self.config = AgentConfig()
        # Mock dependencies
        self.agent = ProjectStrategist(self.config)
        self.agent.redis = AsyncMock()
        self.agent.client = AsyncMock()
        
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"feature_name": "Test", "tasks": []}')]
        self.agent.client.messages.create.return_value = mock_response

    def test_plan_execution(self):
        """
        Test the plan method.
        """
        task_req = TaskRequest(
            id="test-task-001",
            task="Evaluate Phase 2 roadmap",
            context={}
        )
        
        # Run async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(self.agent.plan(task_req))
        loop.close()
        
        self.assertEqual(result.get("status"), "planned")
        self.assertEqual(result.get("task_id"), "test-task-001")
        self.assertTrue("plan" in result)

if __name__ == '__main__':
    unittest.main()
