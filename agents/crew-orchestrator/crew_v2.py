from crewai import Agent, Task, Crew, Process
from typing import List, Dict, Any
import httpx
import os
import json
from langchain_openai import ChatOpenAI

class HyperCodeCrew:
    def __init__(self):
        # Configure the LLM - using Ollama for local, or PERPLEXITY/OpenAI via LiteLLM
        # For this free architecture, we assume local or direct API calls
        self.llm = ChatOpenAI(
            openai_api_base=os.getenv("LLM_API_BASE", "http://localhost:11434/v1"),
            openai_api_key=os.getenv("LLM_API_KEY", "NA"),
            model_name=os.getenv("LLM_MODEL", "tinyllama"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.3"))
        )
        self.agents = self._initialize_agents()
        self.crew = Crew(
            agents=self.agents,
            tasks=[],  # Tasks are added dynamically
            process=Process.hierarchical,
            manager_llm=self.llm,
            verbose=True
        )
    
    def _create_agent_tool(self, agent_name: str, base_url: str):
        """Create a tool that wraps the external agent's API"""
        async def call_agent_task(task_description: str, context: Dict[str, Any] = None) -> str:
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.post(
                        f"{base_url}/execute",
                        json={"task": task_description, "context": context or {}},
                        timeout=300.0
                    )
                    return json.dumps(response.json())
                except Exception as e:
                    return f"Error calling {agent_name}: {str(e)}"
        
        # CrewAI expects tools to be methods with specific signatures or Tool objects
        # For simplicity in this v1 refactor, we are defining the capability description
        return call_agent_task

    def _initialize_agents(self) -> List[Agent]:
        """Initialize the 8 specialized agents as CrewAI Agents"""
        
        # Project Strategist
        strategist = Agent(
            role="Project Strategist",
            goal="Define clear project roadmap and prioritize features",
            backstory="Expert at breaking down complex projects into actionable tasks. Specializes in neurodivergent-friendly planning.",
            llm=self.llm,
            allow_delegation=True,
            verbose=True
        )
        
        # System Architect
        architect = Agent(
            role="System Architect",
            goal="Design scalable, maintainable system architecture",
            backstory="20 years experience designing distributed systems. Prioritizes simplicity and developer experience.",
            llm=self.llm,
            allow_delegation=True,
            verbose=True
        )
        
        # Frontend Specialist
        frontend = Agent(
            role="Frontend Specialist",
            goal="Build accessible, beautiful user interfaces",
            backstory="Expert in React, Vue, accessibility standards. Passionate about neurodivergent-friendly UX design.",
            llm=self.llm,
            allow_delegation=False,
            verbose=True
        )
        
        # Backend Specialist
        backend = Agent(
            role="Backend Specialist",
            goal="Build robust, performant APIs and services",
            backstory="Full-stack engineer with deep Python/Node.js knowledge. Emphasizes clean code and comprehensive testing.",
            llm=self.llm,
            allow_delegation=False,
            verbose=True
        )

        # Database Architect
        db_architect = Agent(
            role="Database Architect",
            goal="Design and optimize database schemas",
            backstory="DBA with expertise in PostgreSQL and Redis. Ensures data integrity and performance.",
            llm=self.llm,
            allow_delegation=False,
            verbose=True
        )

        # QA Engineer
        qa = Agent(
            role="QA Engineer",
            goal="Ensure software quality and reliability",
            backstory="Meticulous tester who finds edge cases. Believes in automated testing and continuous integration.",
            llm=self.llm,
            allow_delegation=False,
            verbose=True
        )

        # DevOps Engineer
        devops = Agent(
            role="DevOps Engineer",
            goal="Streamline deployment and operations",
            backstory="Infrastructure as Code expert. Loves Docker, Kubernetes, and CI/CD pipelines.",
            llm=self.llm,
            allow_delegation=False,
            verbose=True
        )

        # Security Engineer
        security = Agent(
            role="Security Engineer",
            goal="Secure the application and infrastructure",
            backstory="White hat hacker turned defender. Thinks like an attacker to prevent breaches.",
            llm=self.llm,
            allow_delegation=False,
            verbose=True
        )

        return [strategist, architect, frontend, backend, db_architect, qa, devops, security]

    async def execute_workflow(self, workflow_type: str, description: str, context: Dict[str, Any] = None):
        """Execute a predefined workflow using the Crew"""
        
        tasks = []
        
        if workflow_type == "feature":
            # 1. Strategy
            tasks.append(Task(
                description=f"Analyze feature request: {description}. Define requirements and acceptance criteria.",
                agent=self.agents[0], # Strategist
                expected_output="Feature specification and requirements doc"
            ))
            
            # 2. Architecture
            tasks.append(Task(
                description="Design technical architecture for the feature based on requirements.",
                agent=self.agents[1], # Architect
                expected_output="Technical design document",
                context=[tasks[0]]
            ))
            
            # 3. Implementation (Parallel-ish)
            tasks.append(Task(
                description="Implement frontend components based on design.",
                agent=self.agents[2], # Frontend
                expected_output="Frontend code PR",
                context=[tasks[1]]
            ))
            
            tasks.append(Task(
                description="Implement backend APIs based on design.",
                agent=self.agents[3], # Backend
                expected_output="Backend code PR",
                context=[tasks[1]]
            ))
            
        elif workflow_type == "bugfix":
            # Simple bugfix workflow
            tasks.append(Task(
                description=f"Analyze bug report: {description}. Identify root cause.",
                agent=self.agents[3], # Backend (defaulting to backend for analysis)
                expected_output="Root cause analysis"
            ))
            
            tasks.append(Task(
                description="Implement fix and write regression test.",
                agent=self.agents[3], # Backend
                expected_output="Fix commit with tests",
                context=[tasks[0]]
            ))

        # Reset crew tasks and kick off
        self.crew.tasks = tasks
        result = await self.crew.kickoff_async()
        return result
