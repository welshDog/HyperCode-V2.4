"""
Project Strategist Agent
Plans, breaks down, and delegates tasks to specialist agents
"""
import sys
sys.path.append('/app')
from base_agent import BaseAgent, AgentConfig
from typing import Any, Dict, List, Optional
import httpx
import json
import os
import uuid

class ProjectStrategist(BaseAgent):
    
    # Container-internal ports (agents-net, not the host-mapped ports in
    # CLAUDE.md's fleet table) - frontend/backend/database/qa/devops kept
    # their original distinct ports, security/architect were moved to the
    # uniform :8080 convention during the 2026-08-20 port audit (item #9 in
    # docs/NEXT_TASKS.md) - this dict was never updated to match.
    SPECIALIST_AGENTS = {
        "frontend": "http://frontend-specialist:8012",
        "backend": "http://backend-specialist:8003",
        "database": "http://database-architect:8004",
        "qa": "http://qa-engineer:8005",
        "devops": "http://devops-engineer:8006",
        "security": "http://security-engineer:8080",
        "architect": "http://system-architect:8080"
    }
    
    def build_system_prompt(self) -> str:
        base_prompt = super().build_system_prompt()
        return f"""{base_prompt}

**Your Specialization: Project Strategy & Task Delegation**

RESPONSIBILITIES:
- Break down complex features into actionable subtasks
- Identify which specialists are needed for each task
- Create detailed task tickets with acceptance criteria
- Estimate time and complexity
- Coordinate dependencies between tasks
- Monitor overall project progress

TASK BREAKDOWN FORMAT:
1. Analyze the request thoroughly
2. Identify all technical components needed
3. Determine specialist assignments (Frontend, Backend, Database, etc.)
4. Define clear acceptance criteria
5. Establish task order and dependencies
6. Estimate effort (story points or hours)

DELEGATION STRATEGY:
- Frontend Specialist: UI components, styling, client-side logic
- Backend Specialist: APIs, business logic, server operations
- Database Architect: Schema design, queries, migrations
- QA Engineer: Test plans, automation, validation
- DevOps Engineer: CI/CD, deployments, infrastructure
- Security Engineer: Vulnerability scanning, auth implementation
- System Architect: Overall design, patterns, architecture decisions

OUTPUT FORMAT:
Return structured JSON with:
{{
  "feature_name": "...",
  "complexity": "low|medium|high",
  "estimated_hours": 0,
  "tasks": [
    {{
      "id": "TASK-001",
      "title": "...",
      "description": "...",
      "assigned_to": "backend",
      "priority": "high|medium|low",
      "dependencies": ["TASK-000"],
      "acceptance_criteria": ["..."]
    }}
  ]
}}
"""
    
    async def process_task(self, task: str, context: Dict[str, Any], requires_approval: bool = False) -> Any:
        """
        Overrides BaseAgent.process_task so /execute actually reaches plan()
        instead of falling through to the generic LLM passthrough.
        """
        if requires_approval and self.approval_system:
            approval = await self.approval_system.request_approval(
                self.config.name, "execute_task", {"task": task}, timeout=300
            )
            if approval.get("status") != "approved":
                raise RuntimeError(f"Task rejected: {approval.get('reason')}")

        context = context or {}
        task_id = context.get("task_id") or context.get("id") or str(uuid.uuid4())
        return await self.plan(task_id=task_id, task=task, context=context)

    async def plan(self, task_id: str, task: str, context: Optional[Dict] = None) -> Dict:
        """
        Create detailed plan and delegate to specialists
        """
        context = context or {}

        # Get planning from Claude
        system_prompt = self.build_system_prompt()

        message = await self.client.messages.create(
            model=self.config.model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{
                "role": "user",
                "content": f"""Plan this task:

Task: {task}
Context: {json.dumps(context)}

Create a detailed breakdown with specific subtasks for each specialist agent."""
            }]
        )

        result = message.content[0].text

        # Parse the plan. Claude reliably wraps JSON in a ```json ... ```
        # fence despite the prompt asking for raw JSON, and sometimes adds
        # trailing prose after the closing fence - locate the fenced block
        # rather than assuming it spans the whole string.
        text = result.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else ""
            text = text.split("```", 1)[0].strip()

        try:
            plan = json.loads(text)
        except Exception:
            # If still not JSON, wrap it
            plan = {"raw_plan": result, "tasks": []}

        # Store plan in Redis
        if self.redis:
            await self.redis.hset(
                f"task:{task_id}",
                "plan",
                json.dumps(plan)
            )

        # Bridge: submit mission to HyperCode Core for lifecycle tracking
        try:
            feature_name = plan.get("feature_name") or task
            caps = sorted({(t.get("assigned_to") or "").lower() for t in plan.get("tasks", []) if t.get("assigned_to")})
            mission_payload = {
                "plan": plan,
                "requirements": {"capabilities": caps},
                "rollback_plan": plan.get("rollback", []),
            }
            core_url = os.getenv("CORE_URL", "http://hypercode-core:8000")
            async with httpx.AsyncClient(timeout=5.0) as client:
                mr = await client.post(
                    f"{core_url}/orchestrator/mission",
                    json={"title": feature_name, "priority": 80, "payload": mission_payload}
                )
                if mr.status_code == 200 and self.redis:
                    await self.redis.hset(f"task:{task_id}", "mission", mr.text)
        except Exception as e:
            print(f"⚠️ Failed to submit mission to Core: {e}")

        # Delegate to specialists
        await self.delegate_tasks(task_id, plan.get("tasks", []))

        return {
            "task_id": task_id,
            "status": "planned",
            "plan": plan
        }
    
    async def delegate_tasks(self, parent_task_id: str, tasks: List[Dict]):
        """
        Send subtasks to specialist agents
        """
        agent_key = (os.getenv("HYPERCODE_API_KEY") or os.getenv("AGENT_API_KEY") or "").strip()
        headers = {"x-agent-key": agent_key} if agent_key else {}
        async with httpx.AsyncClient() as client:
            for task in tasks:
                agent = task.get("assigned_to")
                if agent in self.SPECIALIST_AGENTS:
                    try:
                        await client.post(
                            f"{self.SPECIALIST_AGENTS[agent]}/execute",
                            json={
                                "task_id": task.get("id"),
                                "task": task.get("description"),
                                "context": {
                                    "parent_task": parent_task_id,
                                    "acceptance_criteria": task.get("acceptance_criteria", [])
                                }
                            },
                            headers=headers,
                            timeout=120.0
                        )
                    except Exception as e:
                        print(f"Failed to delegate to {agent}: {e}")

if __name__ == "__main__":
    config = AgentConfig()
    agent = ProjectStrategist(config)
    agent.run()

