from crewai import Agent, Task, Crew, Process
from typing import List, Dict, Any, Optional
import httpx
import os
import json

# ─── LLM Factory ────────────────────────────────────────────────────────────
def _get_llm(tier: str = "haiku"):
    """
    Tier routing:
      opus   → claude-opus-4-6        (crew manager — deep reasoning)
      sonnet → claude-sonnet-4-5      (heavy agents — code, security, backend)
      haiku  → claude-haiku-3         (light agents — QA, DevOps, Frontend)
      fallback → ollama/llama3.2      (no API key — never goes dark)
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        try:
            from langchain_anthropic import ChatAnthropic
            models = {
                "opus":   "claude-opus-4-6",
                "sonnet": "claude-sonnet-4-5",
                "haiku":  "claude-haiku-3",
            }
            max_tokens = {
                "opus":   8192,
                "sonnet": 4096,
                "haiku":  1024,
            }
            return ChatAnthropic(
                model=models.get(tier, "claude-haiku-3"),
                api_key=api_key,
                max_tokens=max_tokens.get(tier, 1024),
                temperature=float(os.getenv("LLM_TEMPERATURE", "0.3")),
            )
        except ImportError:
            pass  # langchain-anthropic not installed — fall through to Ollama

    # Fallback — Ollama (upgraded from tinyllama → llama3.2)
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        openai_api_base=os.getenv("LLM_API_BASE", "http://ollama:11434/v1"),
        openai_api_key=os.getenv("LLM_API_KEY", "NA"),
        model_name=os.getenv("LLM_MODEL", "llama3.2"),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.3")),
    )


# ─── Shared Bible Context ────────────────────────────────────────────────────
def _load_bible() -> str:
    """Load HYPER-AGENT-BIBLE.md as shared system context for all agents."""
    bible_path = os.path.join(os.path.dirname(__file__), "HYPER-AGENT-BIBLE.md")
    if os.path.exists(bible_path):
        with open(bible_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


BIBLE = _load_bible()


# ─── Crew ────────────────────────────────────────────────────────────────────
class HyperCodeCrew:
    def __init__(self):
        self.manager_llm = _get_llm("opus")
        self.agents = self._initialize_agents()
        self.crew = Crew(
            agents=self.agents,
            tasks=[],
            process=Process.hierarchical,
            manager_llm=self.manager_llm,
            verbose=True,
        )

    def _agent(self, role, goal, backstory, tier="haiku", delegate=False) -> Agent:
        """Helper — injects BIBLE into every backstory automatically."""
        full_backstory = f"{backstory}\n\n---\n{BIBLE}" if BIBLE else backstory
        return Agent(
            role=role,
            goal=goal,
            backstory=full_backstory,
            llm=_get_llm(tier),
            allow_delegation=delegate,
            verbose=True,
            max_iter=int(os.getenv("AGENT_MAX_ITER", "15")),
        )

    def _initialize_agents(self) -> List[Agent]:
        return [
            # ── Sonnet tier (heavy reasoning) ──
            self._agent(
                role="Project Strategist",
                goal="Define clear project roadmap and prioritise features",
                backstory="Expert at breaking complex projects into neurodivergent-friendly actionable tasks.",
                tier="sonnet",
                delegate=True,
            ),
            self._agent(
                role="System Architect",
                goal="Design scalable, maintainable system architecture",
                backstory="20 years designing distributed systems. Prioritises simplicity and developer experience.",
                tier="sonnet",
                delegate=True,
            ),
            self._agent(
                role="Backend Specialist",
                goal="Build robust, performant APIs and services",
                backstory="Full-stack Python engineer. Clean code, comprehensive testing, never breaks Sacred Rules.",
                tier="sonnet",
            ),
            self._agent(
                role="Database Architect",
                goal="Design and optimise database schemas",
                backstory="PostgreSQL + Redis DBA. Never mixes Redis DB1/DB2. Alembic per-service always.",
                tier="sonnet",
            ),
            self._agent(
                role="Security Engineer",
                goal="Secure the application and infrastructure",
                backstory="White hat hacker turned defender. Always REVOKE FROM PUBLIC first, not anon/authenticated.",
                tier="sonnet",
            ),
            self._agent(
                role="Coder Agent",
                goal="Write clean, tested, production-ready code",
                backstory="Elite coder. 4-space indent always. from app.X import Y never from backend.app.X.",
                tier="sonnet",
            ),
            # ── Haiku tier (fast, lightweight) ──
            self._agent(
                role="Frontend Specialist",
                goal="Build accessible, beautiful, neurodivergent-friendly UIs",
                backstory="React expert. Accessibility-first. npm run dev:frontend ONLY, never npm run dev.",
                tier="haiku",
            ),
            self._agent(
                role="QA Engineer",
                goal="Ensure software quality and reliability",
                backstory="Meticulous tester. Finds edge cases. Believes in automated testing and CI.",
                tier="haiku",
            ),
            self._agent(
                role="DevOps Engineer",
                goal="Streamline deployment and operations",
                backstory="IaC expert. docker-ce-cli ONLY never docker.io. Stripe webhook rate-limit exempt always.",
                tier="haiku",
            ),
        ]

    def _create_agent_tool(self, agent_name: str, base_url: str):
        """Wrap external agent HTTP API as a callable tool."""
        async def call_agent_task(
            task_description: str, context: Dict[str, Any] = None
        ) -> str:
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.post(
                        f"{base_url}/execute",
                        json={"task": task_description, "context": context or {}},
                        timeout=300.0,
                    )
                    return json.dumps(response.json())
                except Exception as e:
                    return f"Error calling {agent_name}: {str(e)}"
        return call_agent_task

    async def execute_workflow(
        self,
        workflow_type: str,
        description: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Execute a predefined workflow using the Crew."""
        tasks: List[Task] = []
        ctx = context or {}

        # Index helpers
        strategist, architect, backend, db, security, coder, frontend, qa, devops = (
            self.agents
        )

        if workflow_type == "feature":
            tasks.append(Task(
                description=f"Analyse feature request: {description}. Define requirements and acceptance criteria.",
                agent=strategist,
                expected_output="Feature specification and requirements doc",
            ))
            tasks.append(Task(
                description="Design technical architecture for the feature based on requirements.",
                agent=architect,
                expected_output="Technical design document",
                context=[tasks[0]],
            ))
            tasks.append(Task(
                description="Implement frontend components based on design.",
                agent=frontend,
                expected_output="Frontend code + component list",
                context=[tasks[1]],
            ))
            tasks.append(Task(
                description="Implement backend APIs based on design.",
                agent=backend,
                expected_output="Backend code + API spec",
                context=[tasks[1]],
            ))
            tasks.append(Task(
                description="Review implementation for security vulnerabilities.",
                agent=security,
                expected_output="Security review report",
                context=[tasks[2], tasks[3]],
            ))
            tasks.append(Task(
                description="Write and run tests for the feature.",
                agent=qa,
                expected_output="Test results + coverage report",
                context=[tasks[2], tasks[3]],
            ))

        elif workflow_type == "bugfix":
            tasks.append(Task(
                description=f"Analyse bug report: {description}. Identify root cause.",
                agent=backend,
                expected_output="Root cause analysis",
            ))
            tasks.append(Task(
                description="Implement fix and write regression test.",
                agent=coder,
                expected_output="Fix commit with tests",
                context=[tasks[0]],
            ))
            tasks.append(Task(
                description="Verify fix and confirm no regressions.",
                agent=qa,
                expected_output="QA sign-off",
                context=[tasks[1]],
            ))

        elif workflow_type == "security_audit":
            tasks.append(Task(
                description=f"Run full security audit: {description}",
                agent=security,
                expected_output="Security audit report with CVSS scores",
            ))
            tasks.append(Task(
                description="Review DB permissions, RLS policies, and migration isolation.",
                agent=db,
                expected_output="DB security report",
                context=[tasks[0]],
            ))

        elif workflow_type == "infra_check":
            tasks.append(Task(
                description=f"Infrastructure health check: {description}",
                agent=devops,
                expected_output="Infrastructure status report",
            ))

        else:
            # Generic single-strategist task
            tasks.append(Task(
                description=description,
                agent=strategist,
                expected_output="Task completion report",
            ))

        self.crew.tasks = tasks
        result = await self.crew.kickoff_async()
        return result
