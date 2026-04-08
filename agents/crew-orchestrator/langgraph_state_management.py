#!/usr/bin/env python3
"""
Crew Orchestrator → LangGraph State Management Layer
====================================================

Refactor crew-orchestrator to use LangGraph-style state graphs for:
1. Deterministic agent composition + control flow
2. State persistence across agent calls
3. Tool/goal sequencing
4. Easy multi-agent workflows

This allows the crew to function like:
  [Task] → [Agent A] → [State] → [Agent B] → [State] → [Agent C] → [Result]

With branching, parallel execution, loops, and checkpoints.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import asyncio

# LangGraph-style abstractions (you can use actual LangGraph library too)


class AgentRole(Enum):
    """Agent roles in the crew"""
    STRATEGIST = "strategist"
    DEVELOPER = "developer"
    TESTER = "tester"
    DEVOPS = "devops"
    SECURITY = "security"


@dataclass
class AgentDecision:
    """A single agent's decision/output"""
    agent_role: AgentRole
    task: str
    decision: str
    reasoning: str
    confidence: float  # 0.0 - 1.0
    tools_used: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class WorkflowState:
    """
    Shared state for all agents in crew.
    Persists across agent calls, allowing stateful reasoning.
    """
    # Task definition
    task_id: str
    task_description: str
    goal: str
    
    # Shared context
    project_context: Dict[str, Any] = field(default_factory=dict)
    codebase_info: Dict[str, Any] = field(default_factory=dict)
    previous_decisions: List[AgentDecision] = field(default_factory=list)
    
    # Dynamic state (updated as agents execute)
    current_stage: str = "planning"  # planning → development → testing → deployment
    current_agent: Optional[AgentRole] = None
    
    # Accumulated results
    decisions: List[AgentDecision] = field(default_factory=list)
    artifacts: Dict[str, Any] = field(default_factory=dict)  # Generated code, configs, etc.
    errors: List[str] = field(default_factory=list)
    
    # Control flow
    approved_by: List[AgentRole] = field(default_factory=list)  # Who approved each stage
    needs_approval: bool = False
    is_approved: bool = False
    
    # Execution metadata
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: str = "pending"  # pending → running → completed → failed


class WorkflowNode:
    """Represents a single node in the execution graph"""
    
    def __init__(self, name: str, agent_role: AgentRole):
        self.name = name
        self.agent_role = agent_role
        self.edges: List[str] = []  # Next nodes
        
    async def execute(self, state: WorkflowState) -> WorkflowState:
        """Execute this node. Override in subclass."""
        raise NotImplementedError


class StateGraph:
    """LangGraph-style state graph for HyperCode crew"""
    
    def __init__(self):
        self.nodes: Dict[str, WorkflowNode] = {}
        self.edges: Dict[str, List[str]] = {}
        self.entry_point: Optional[str] = None
        self.end_point: Optional[str] = None
    
    def add_node(self, name: str, node: WorkflowNode):
        self.nodes[name] = node
    
    def add_edge(self, source: str, target: str):
        if source not in self.edges:
            self.edges[source] = []
        self.edges[source].append(target)
        # Update node's edges too
        if source in self.nodes:
            self.nodes[source].edges.append(target)
    
    def set_entry_point(self, name: str):
        self.entry_point = name
    
    def set_end_point(self, name: str):
        self.end_point = name
    
    async def compile_and_run(self, initial_state: WorkflowState) -> WorkflowState:
        """Execute the graph from entry to end point"""
        state = initial_state
        current_node = self.entry_point
        visited = set()
        
        while current_node and current_node != self.end_point:
            if current_node in visited:
                raise RuntimeError(f"Cycle detected at {current_node}")
            visited.add(current_node)
            
            print(f"\n🔄 Executing: {current_node}")
            state.current_stage = current_node
            
            node = self.nodes.get(current_node)
            if not node:
                raise ValueError(f"Unknown node: {current_node}")
            
            # Execute the node
            state = await node.execute(state)
            
            # Determine next node
            next_nodes = self.edges.get(current_node, [])
            if len(next_nodes) == 0:
                break
            elif len(next_nodes) == 1:
                current_node = next_nodes[0]
            else:
                # Multiple edges - pick based on state (e.g., approve/reject)
                current_node = self._select_next_node(state, next_nodes)
        
        state.end_time = datetime.utcnow().isoformat()
        state.status = "completed"
        return state
    
    def _select_next_node(
        self, state: WorkflowState, options: List[str]
    ) -> Optional[str]:
        """Select next node based on state (branching logic)"""
        if state.needs_approval and not state.is_approved:
            # If approval needed but not approved, maybe return to approval node
            approval_nodes = [n for n in options if "approval" in n.lower()]
            return approval_nodes[0] if approval_nodes else options[0]
        return options[0]  # Default: take first edge


# ============================================================================
# EXAMPLE WORKFLOW NODES
# ============================================================================

class PlanningNode(WorkflowNode):
    """Project strategist plans the work"""
    
    async def execute(self, state: WorkflowState) -> WorkflowState:
        print(f"📋 Planning: {state.goal}")
        
        state.current_agent = AgentRole.STRATEGIST
        
        decision = AgentDecision(
            agent_role=AgentRole.STRATEGIST,
            task=state.task_description,
            decision="Detailed plan created",
            reasoning="Analyzed requirements and created 3-phase roadmap",
            confidence=0.95,
            tools_used=["github:analyze_repo", "vectordb:search"],
        )
        state.decisions.append(decision)
        state.artifacts["plan.md"] = """
        # Execution Plan
        
        ## Phase 1: Setup (30 min)
        - [ ] Initialize project
        - [ ] Set up CI/CD
        
        ## Phase 2: Development (2 hours)
        - [ ] Implement core feature
        - [ ] Write tests
        
        ## Phase 3: Review & Deploy (1 hour)
        - [ ] Code review
        - [ ] Deploy to staging
        """
        
        return state


class DevelopmentNode(WorkflowNode):
    """Backend specialist develops the feature"""
    
    async def execute(self, state: WorkflowState) -> WorkflowState:
        print(f"💻 Developing: {state.task_description}")
        
        state.current_agent = AgentRole.DEVELOPER
        
        decision = AgentDecision(
            agent_role=AgentRole.DEVELOPER,
            task=f"Implement {state.goal}",
            decision="Feature implemented and unit tested",
            reasoning="Followed design from planning phase, all unit tests passing",
            confidence=0.88,
            tools_used=["filesystem:write", "github:create_pull_request"],
        )
        state.decisions.append(decision)
        state.artifacts["feature.py"] = """
        # Generated feature code
        def new_feature():
            pass
        """
        
        # Mark as needing approval before moving to testing
        state.needs_approval = True
        
        return state


class TestingNode(WorkflowNode):
    """QA engineer tests the feature"""
    
    async def execute(self, state: WorkflowState) -> WorkflowState:
        print(f"🧪 Testing: {state.task_description}")
        
        state.current_agent = AgentRole.TESTER
        
        decision = AgentDecision(
            agent_role=AgentRole.TESTER,
            task=f"Test {state.goal}",
            decision="All tests passed",
            reasoning="Integration tests, performance tests, edge case coverage: 95%",
            confidence=0.92,
            tools_used=["filesystem:read", "postgres:execute_query"],
        )
        state.decisions.append(decision)
        state.artifacts["test_report.json"] = {
            "passed": 42,
            "failed": 0,
            "coverage": 0.95,
        }
        
        return state


class ApprovalNode(WorkflowNode):
    """Security engineer approves deployment"""
    
    async def execute(self, state: WorkflowState) -> WorkflowState:
        print(f"🔒 Security Review: {state.task_description}")
        
        state.current_agent = AgentRole.SECURITY
        
        decision = AgentDecision(
            agent_role=AgentRole.SECURITY,
            task=f"Approve {state.goal}",
            decision="APPROVED for production",
            reasoning="No security vulnerabilities detected, dependencies scanned",
            confidence=0.98,
            tools_used=["security-scanner"],
        )
        state.decisions.append(decision)
        state.approved_by.append(AgentRole.SECURITY)
        state.is_approved = True
        state.needs_approval = False
        
        return state


class DeploymentNode(WorkflowNode):
    """DevOps engineer deploys the feature"""
    
    async def execute(self, state: WorkflowState) -> WorkflowState:
        print(f"🚀 Deploying: {state.task_description}")
        
        state.current_agent = AgentRole.DEVOPS
        
        decision = AgentDecision(
            agent_role=AgentRole.DEVOPS,
            task=f"Deploy {state.goal}",
            decision="Deployed to production successfully",
            reasoning="Zero-downtime deploy, health checks passing, monitoring active",
            confidence=0.99,
            tools_used=["docker-compose", "kubectl", "monitoring"],
        )
        state.decisions.append(decision)
        state.artifacts["deployment_log"] = """
        [2026-03-14 10:00:00] Starting deployment
        [2026-03-14 10:00:15] Health checks passing
        [2026-03-14 10:00:30] Deployment complete
        """
        
        return state


# ============================================================================
# BUILD THE CREW WORKFLOW
# ============================================================================

def build_hypercode_crew_workflow() -> StateGraph:
    """Construct the full HyperCode crew workflow"""
    
    graph = StateGraph()
    
    # Create nodes
    planning = PlanningNode("planning", AgentRole.STRATEGIST)
    development = DevelopmentNode("development", AgentRole.DEVELOPER)
    testing = TestingNode("testing", AgentRole.TESTER)
    approval = ApprovalNode("approval", AgentRole.SECURITY)
    deployment = DeploymentNode("deployment", AgentRole.DEVOPS)
    
    # Add to graph
    graph.add_node("planning", planning)
    graph.add_node("development", development)
    graph.add_node("testing", testing)
    graph.add_node("approval", approval)
    graph.add_node("deployment", deployment)
    
    # Define edges (execution order + branches)
    graph.add_edge("planning", "development")
    graph.add_edge("development", "testing")
    graph.add_edge("testing", "approval")
    graph.add_edge("approval", "deployment")
    
    # Set entry/end points
    graph.set_entry_point("planning")
    graph.set_end_point("deployment")
    
    return graph


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

async def main():
    """Run the crew orchestrator with LangGraph state management"""
    
    # Build workflow
    workflow = build_hypercode_crew_workflow()
    
    # Create initial state
    initial_state = WorkflowState(
        task_id="task-001",
        task_description="Implement real-time notifications feature",
        goal="Add WebSocket-based notifications to BROski dashboard",
        project_context={
            "repo": "welshDog/HyperCode-V2.0",
            "language": "Python",
            "framework": "FastAPI",
        },
        start_time=datetime.utcnow().isoformat(),
    )
    
    # Execute workflow
    print("🚀 Starting HyperCode Crew Workflow")
    print(f"   Task: {initial_state.goal}")
    
    final_state = await workflow.compile_and_run(initial_state)
    
    # Print results
    print("\n" + "=" * 70)
    print("✅ WORKFLOW COMPLETED")
    print("=" * 70)
    
    print("\n📊 Summary:")
    print(f"   Status: {final_state.status}")
    print(f"   Decisions: {len(final_state.decisions)}")
    print(f"   Artifacts: {list(final_state.artifacts.keys())}")
    print(f"   Approved: {final_state.is_approved}")
    
    print("\n🔍 Agent Decisions:")
    for decision in final_state.decisions:
        print(f"   {decision.agent_role.value.upper()}: {decision.decision} (confidence: {decision.confidence})")
    
    print("\n💾 Generated Artifacts:")
    for name, content in final_state.artifacts.items():
        print(f"   - {name} ({len(str(content))} bytes)")
    
    print("\n📝 Approval Chain:")
    for agent in final_state.approved_by:
        print(f"   ✓ {agent.value}")


if __name__ == "__main__":
    asyncio.run(main())
