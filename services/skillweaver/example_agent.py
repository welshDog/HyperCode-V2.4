"""
Example: Backend Specialist Agent Using SkillWeaver
===================================================

This shows a real agent integrating SkillWeaver to discover and use
skills from other agents.

This is a complete, copy-paste example you can adapt for your agents.
"""

import asyncio
import logging
from typing import Any, Dict

from services.skillweaver.sdk import SkillWeaverClient, discover_and_compose

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BackendSpecialistAgent:
    """
    Backend specialist that can:
    1. Execute core backend tasks
    2. Discover skills from other agents
    3. Compose them into new capabilities
    4. Execute composite skills
    """
    
    def __init__(self, agent_id: str, skillweaver_url: str = "http://skillweaver:8051"):
        self.agent_id = agent_id
        self.skillweaver = SkillWeaverClient(skillweaver_url)
        self.registered_skills = []
        self.executed_tasks = []
    
    async def startup(self):
        """Initialize agent and register skills."""
        logger.info(f"[{self.agent_id}] Starting up...")
        
        # Register core skills
        skills_to_register = [
            (
                "execute_backend_task",
                "Execute Backend Task",
                "Execute core backend operations with error recovery",
                {"task_type": "str", "payload": "dict"},
                {"result": "dict", "success": "bool"},
            ),
            (
                "database_query",
                "Database Query",
                "Query database and return results",
                {"query": "str", "params": "dict"},
                {"rows": "list", "count": "int"},
            ),
            (
                "api_request",
                "API Request",
                "Make HTTP API requests to external services",
                {"endpoint": "str", "method": "str", "body": "dict"},
                {"response": "dict", "status": "int"},
            ),
        ]
        
        for skill_id, name, desc, inputs, outputs in skills_to_register:
            try:
                result = await self.skillweaver.register_skill(
                    skill_id=skill_id,
                    agent_id=self.agent_id,
                    name=name,
                    description=desc,
                    category="computation",
                    inputs=inputs,
                    outputs=outputs,
                    version="1.0.0",
                )
                self.registered_skills.append(skill_id)
                logger.info(f"[{self.agent_id}] ✅ Registered skill: {name}")
            except Exception as e:
                logger.warning(f"[{self.agent_id}] ⚠️  Failed to register {skill_id}: {e}")
        
        logger.info(f"[{self.agent_id}] Ready! ({len(self.registered_skills)} skills registered)")
    
    async def handle_standard_task(self, task_description: str) -> Dict[str, Any]:
        """Handle a standard task using built-in skills."""
        logger.info(f"[{self.agent_id}] Handling standard task: {task_description}")
        
        # Simulate task execution
        result = {
            "task": task_description,
            "success": True,
            "result": "Task executed successfully",
        }
        
        self.executed_tasks.append(result)
        return result
    
    async def handle_novel_task(self, task_description: str) -> Dict[str, Any]:
        """
        Handle a novel task by discovering and composing skills from other agents.
        
        This is the WOW part: agent automatically discovers capabilities it doesn't
        natively have, composes them, and executes.
        """
        logger.info(f"[{self.agent_id}] 🔥 Handling NOVEL task: {task_description}")
        
        # Step 1: Try our standard approach first
        try:
            result = await self.handle_standard_task(task_description)
            if result["success"]:
                return result
        except Exception as e:
            logger.warning(f"[{self.agent_id}] Standard approach failed: {e}")
        
        # Step 2: Query SkillWeaver for relevant skills
        logger.info(f"[{self.agent_id}] 🔍 Querying SkillWeaver for relevant skills...")
        try:
            matches = await self.skillweaver.discover_skills(
                query=task_description,
                top_k=3
            )
            
            if not matches:
                logger.error(f"[{self.agent_id}] ❌ No skills found for: {task_description}")
                return {
                    "task": task_description,
                    "success": False,
                    "error": "No applicable skills found",
                }
            
            logger.info(f"[{self.agent_id}] 🎯 Found {len(matches)} relevant skills:")
            for i, match in enumerate(matches, 1):
                logger.info(f"   {i}. {match['name']} (score: {match['relevance_score']:.2f})")
                logger.info(f"      Agent: {match['agent_id']}")
                logger.info(f"      Description: {match['description']}")
        
        except Exception as e:
            logger.error(f"[{self.agent_id}] Skill discovery failed: {e}")
            return {"task": task_description, "success": False, "error": str(e)}
        
        # Step 3: Compose the top matches
        logger.info(f"[{self.agent_id}] 🧬 Composing skills into a new capability...")
        try:
            composite = await discover_and_compose(
                self.skillweaver,
                task_description,
                top_k=min(2, len(matches)),
            )
            
            if not composite:
                logger.error(f"[{self.agent_id}] ❌ Composition failed")
                return {
                    "task": task_description,
                    "success": False,
                    "error": "Composition failed",
                }
        
        except Exception as e:
            logger.error(f"[{self.agent_id}] Composition error: {e}")
            return {"task": task_description, "success": False, "error": str(e)}
        
        # Step 4: Execute the composite skill
        logger.info(f"[{self.agent_id}] ⚡ Executing composite skill: {composite}")
        try:
            # Simulate composite execution
            result = {
                "task": task_description,
                "success": True,
                "method": "composite_skill",
                "composite_id": composite,
                "result": "Task executed via skill composition",
            }
            
            self.executed_tasks.append(result)
            logger.info(f"[{self.agent_id}] ✅ Task completed via skill composition!")
            return result
        
        except Exception as e:
            logger.error(f"[{self.agent_id}] Composite execution failed: {e}")
            return {"task": task_description, "success": False, "error": str(e)}
    
    async def handle_task(self, task_description: str) -> Dict[str, Any]:
        """
        Main task handler.
        Automatically decides whether to use standard or novel approach.
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"[{self.agent_id}] New task: {task_description}")
        logger.info(f"{'='*70}")
        
        # Keywords that suggest a novel task requiring skill composition
        novel_keywords = [
            "optimize",
            "improve",
            "analyze",
            "combine",
            "integrate",
            "hybrid",
            "smart",
            "advanced",
        ]
        
        is_novel = any(kw in task_description.lower() for kw in novel_keywords)
        
        if is_novel:
            logger.info(f"[{self.agent_id}] 🎯 Detected novel task, using skill synthesis")
            return await self.handle_novel_task(task_description)
        else:
            logger.info(f"[{self.agent_id}] 📋 Standard task, using built-in skills")
            return await self.handle_standard_task(task_description)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        try:
            skillweaver_stats = await self.skillweaver.stats()
        except:
            skillweaver_stats = {}
        
        return {
            "agent_id": self.agent_id,
            "registered_skills": len(self.registered_skills),
            "tasks_executed": len(self.executed_tasks),
            "successful_tasks": sum(1 for t in self.executed_tasks if t.get("success", False)),
            "success_rate": (
                sum(1 for t in self.executed_tasks if t.get("success", False)) / len(self.executed_tasks)
                if self.executed_tasks else 0.0
            ),
            "skillweaver": {
                "total_skills": skillweaver_stats.get("total_skills", 0),
                "total_compositions": skillweaver_stats.get("total_compositions", 0),
            }
        }
    
    async def shutdown(self):
        """Cleanup."""
        await self.skillweaver.close()
        logger.info(f"[{self.agent_id}] Shut down")


# ============================================================================
# Example Usage
# ============================================================================

async def main():
    """Run the example agent."""
    agent = BackendSpecialistAgent("backend-specialist", "http://localhost:8051")
    
    try:
        # Startup and register skills
        await agent.startup()
        
        # Example 1: Standard task
        print("\n" + "="*70)
        print("EXAMPLE 1: Standard Task")
        print("="*70)
        result1 = await agent.handle_task("Deploy a new API endpoint")
        print(f"Result: {result1}")
        
        # Example 2: Novel task (would use skill composition)
        print("\n" + "="*70)
        print("EXAMPLE 2: Novel Task (Skill Synthesis)")
        print("="*70)
        result2 = await agent.handle_task("Deploy an API with cost optimization and quality checks")
        print(f"Result: {result2}")
        
        # Example 3: Get statistics
        print("\n" + "="*70)
        print("AGENT STATISTICS")
        print("="*70)
        stats = await agent.get_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")
    
    finally:
        await agent.shutdown()


if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════════════════════╗
    ║                                                                          ║
    ║         Backend Specialist Agent with SkillWeaver Integration           ║
    ║                                                                          ║
    ║  This agent demonstrates:                                               ║
    ║    ✅ Registering skills with SkillWeaver                               ║
    ║    ✅ Discovering skills from other agents                              ║
    ║    ✅ Composing them into new capabilities                              ║
    ║    ✅ Executing composite skills                                        ║
    ║                                                                          ║
    ║  Before running:                                                        ║
    ║    1. Start SkillWeaver: docker compose up -d skillweaver               ║
    ║    2. Ensure Redis is running                                           ║
    ║                                                                          ║
    ║  Run with: python services/skillweaver/example_agent.py                 ║
    ║                                                                          ║
    ╚══════════════════════════════════════════════════════════════════════════╝
    """)
    
    asyncio.run(main())
