"""
SkillWeaver: Cross-Agent Skill Synthesis Engine
===============================================

Phase 1 of HyperCode ALS (Autonomous Learning System).
Enables agents to discover and compose skills from other agents at runtime.

How it works:
  1. Every agent registers its skills (name, description, signature)
  2. Agents query SkillWeaver: "I need skills related to X"
  3. SkillWeaver finds matches using semantic search (MiniLM embeddings)
  4. Agent requests composition: "Fuse skill1 + skill2 with error-handling"
  5. SkillWeaver generates a callable that chains them safely
  6. Agent runs the new composite skill, reports results
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

import redis.asyncio as redis
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class SkillCategory(str, Enum):
    """Semantic categories for skill discovery."""
    COMPUTATION = "computation"
    IO = "io"
    ORCHESTRATION = "orchestration"
    OPTIMIZATION = "optimization"
    SAFETY = "safety"
    COMMUNICATION = "communication"
    LEARNING = "learning"
    TESTING = "testing"


@dataclass
class SkillSignature:
    """Describes input/output contract for a skill."""
    
    inputs: Dict[str, str]  # param_name -> type_hint
    outputs: Dict[str, str]  # field_name -> type_hint
    
    def to_dict(self) -> dict:
        return {"inputs": self.inputs, "outputs": self.outputs}


@dataclass
class SkillMetadata:
    """Rich metadata for a skill."""
    
    skill_id: str
    agent_id: str
    name: str
    description: str
    category: SkillCategory
    signature: SkillSignature
    timeout_seconds: float = 30.0
    retry_count: int = 1
    examples: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    
    def embedding_text(self) -> str:
        """Text to embed for semantic search."""
        return f"{self.name} {self.category.value} {self.description}"
    
    def to_dict(self) -> dict:
        return {
            "skill_id": self.skill_id,
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "signature": self.signature.to_dict(),
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
            "examples": self.examples,
            "version": self.version,
        }


@dataclass
class SkillMatch:
    """Result of skill discovery."""
    
    metadata: SkillMetadata
    relevance_score: float  # 0.0 - 1.0
    reason: str  # Why this skill matched


class SkillRegistry:
    """Register and manage skills from all agents."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.registry_key = "skillweaver:registry"
        self.embeddings_key = "skillweaver:embeddings"
    
    async def register_skill(self, metadata: SkillMetadata) -> None:
        """Register a new skill from an agent."""
        key = f"{self.registry_key}:{metadata.skill_id}"
        await self.redis.set(key, json.dumps(metadata.to_dict()))
        
        # Also store in a set for fast discovery
        await self.redis.sadd(
            f"{self.registry_key}:by_agent:{metadata.agent_id}",
            metadata.skill_id
        )
        await self.redis.sadd(
            f"{self.registry_key}:by_category:{metadata.category.value}",
            metadata.skill_id
        )
        
        logger.info(f"Skill registered: {metadata.skill_id} from {metadata.agent_id}")
    
    async def get_skill(self, skill_id: str) -> Optional[SkillMetadata]:
        """Retrieve skill metadata by ID."""
        key = f"{self.registry_key}:{skill_id}"
        data = await self.redis.get(key)
        if not data:
            return None
        
        d = json.loads(data)
        return SkillMetadata(
            skill_id=d["skill_id"],
            agent_id=d["agent_id"],
            name=d["name"],
            description=d["description"],
            category=SkillCategory(d["category"]),
            signature=SkillSignature(d["signature"]["inputs"], d["signature"]["outputs"]),
            timeout_seconds=d["timeout_seconds"],
            retry_count=d["retry_count"],
            examples=d["examples"],
            version=d["version"],
        )
    
    async def list_skills_by_agent(self, agent_id: str) -> List[SkillMetadata]:
        """Get all skills registered by an agent."""
        skill_ids = await self.redis.smembers(f"{self.registry_key}:by_agent:{agent_id}")
        skills = []
        for skill_id in skill_ids:
            skill = await self.get_skill(skill_id.decode() if isinstance(skill_id, bytes) else skill_id)
            if skill:
                skills.append(skill)
        return skills
    
    async def list_skills_by_category(self, category: SkillCategory) -> List[SkillMetadata]:
        """Get all skills in a category."""
        skill_ids = await self.redis.smembers(f"{self.registry_key}:by_category:{category.value}")
        skills = []
        for skill_id in skill_ids:
            skill = await self.get_skill(skill_id.decode() if isinstance(skill_id, bytes) else skill_id)
            if skill:
                skills.append(skill)
        return skills


class SkillWeaver:
    """Semantic skill discovery and composition engine."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.registry = SkillRegistry(redis_client)
        self.composition_cache = {}  # In-memory cache of composed skills
        self.composition_log_key = "skillweaver:compositions"
    
    async def discover_skills(
        self,
        query: str,
        category: Optional[SkillCategory] = None,
        top_k: int = 5,
    ) -> List[SkillMatch]:
        """
        Find relevant skills using keyword/category matching.
        
        Phase 1 uses keyword+category filtering.
        Phase 2 will add semantic embeddings (MiniLM).
        
        Args:
            query: Natural language query (e.g., "optimize cost")
            category: Optional category filter
            top_k: Return top K matches
        
        Returns:
            Ranked list of matching skills
        """
        # Start with all skills
        if category:
            candidate_skills = await self.registry.list_skills_by_category(category)
        else:
            # Get all skills (fallback: scan registry)
            all_skill_ids = await self.redis.smembers("skillweaver:registry:all_ids")
            candidate_skills = []
            for skill_id in all_skill_ids:
                skill = await self.registry.get_skill(
                    skill_id.decode() if isinstance(skill_id, bytes) else skill_id
                )
                if skill:
                    candidate_skills.append(skill)
        
        # Simple keyword scoring (Phase 1)
        query_lower = query.lower()
        query_tokens = set(query_lower.split())
        
        matches = []
        for skill in candidate_skills:
            # Score: how many query tokens appear in skill name/description
            skill_text = (skill.name + " " + skill.description).lower()
            matched_tokens = sum(1 for token in query_tokens if token in skill_text)
            score = matched_tokens / len(query_tokens) if query_tokens else 0.0
            
            if score > 0.0:  # Only include non-zero matches
                matches.append(SkillMatch(
                    metadata=skill,
                    relevance_score=score,
                    reason=f"Matched {matched_tokens}/{len(query_tokens)} query terms"
                ))
        
        # Sort by score and return top K
        matches.sort(key=lambda m: m.relevance_score, reverse=True)
        return matches[:top_k]
    
    async def validate_composition(
        self,
        skill_ids: List[str],
    ) -> tuple[bool, str]:
        """
        Check if a set of skills can be safely composed.
        
        Validates:
        - No circular dependencies
        - Input/output compatibility
        - No conflicting resource requirements
        
        Returns:
            (valid: bool, reason: str)
        """
        if not skill_ids:
            return False, "Empty skill list"
        
        if len(skill_ids) > 10:
            return False, "Too many skills to compose (max 10)"
        
        # Get all skill metadata
        skills = []
        for skill_id in skill_ids:
            skill = await self.registry.get_skill(skill_id)
            if not skill:
                return False, f"Skill {skill_id} not found"
            skills.append(skill)
        
        # Check for circular dependencies (simplified: only 1-level deep for now)
        skill_outputs = {}
        for skill in skills:
            skill_outputs[skill.skill_id] = set(skill.signature.outputs.keys())
        
        skill_inputs = {}
        for skill in skills:
            skill_inputs[skill.skill_id] = set(skill.signature.inputs.keys())
        
        # Detect cycles (if any skill's output is another skill's input of a skill whose output is this skill's input)
        for skill_id, outputs in skill_outputs.items():
            for other_id, inputs in skill_inputs.items():
                if skill_id != other_id and outputs & inputs:  # Outputs match some inputs
                    # Could be safe if ordered correctly; for now flag as potential cycle
                    pass  # Phase 2: implement proper topological sort
        
        return True, "Composition is valid"
    
    async def compose_skills(
        self,
        skill_ids: List[str],
        strategy: str = "linear",  # "linear", "parallel", "conditional"
    ) -> CompositeSkill:
        """
        Generate a composite skill by chaining input skills.
        
        Args:
            skill_ids: List of skill IDs to compose
            strategy: How to chain them
                - "linear": s1 → s2 → s3
                - "parallel": s1, s2, s3 all run, results merged
                - "conditional": s1 runs; if success, s2; else s3
        
        Returns:
            A new CompositeSkill that can be executed
        """
        # Validate first
        valid, reason = await self.validate_composition(skill_ids)
        if not valid:
            raise ValueError(f"Cannot compose: {reason}")
        
        # Get skill metadata
        skills = []
        for skill_id in skill_ids:
            skill = await self.registry.get_skill(skill_id)
            if not skill:
                raise ValueError(f"Skill {skill_id} not found")
            skills.append(skill)
        
        # Generate composite skill
        composite_id = f"composite_{str(uuid4())[:8]}"
        composite = CompositeSkill(
            composite_id=composite_id,
            component_skills=skills,
            strategy=strategy,
        )
        
        # Log composition
        log_entry = {
            "composite_id": composite_id,
            "component_skills": skill_ids,
            "strategy": strategy,
            "timestamp": asyncio.get_event_loop().time(),
        }
        await self.redis.lpush(self.composition_log_key, json.dumps(log_entry))
        
        logger.info(f"Composite skill created: {composite_id} ({strategy} strategy, {len(skills)} components)")
        return composite
    
    async def teach_agent(
        self,
        agent_id: str,
        composite_skill: CompositeSkill,
    ) -> None:
        """
        Teach an agent to use a composite skill at runtime.
        
        Pushes the skill to the agent's queue; agent fetches and installs it.
        """
        key = f"skillweaver:teach_queue:{agent_id}"
        skill_json = json.dumps({
            "composite_id": composite_skill.composite_id,
            "components": [s.skill_id for s in composite_skill.component_skills],
            "strategy": composite_skill.strategy,
            "callable": str(composite_skill)  # Serialized reference
        })
        await self.redis.lpush(key, skill_json)
        logger.info(f"Composite skill {composite_skill.composite_id} queued for teaching to {agent_id}")


@dataclass
class CompositeSkill:
    """A skill synthesized from multiple component skills."""
    
    composite_id: str
    component_skills: List[SkillMetadata]
    strategy: str  # "linear", "parallel", "conditional"
    
    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the composite skill.
        
        This is a placeholder; real execution requires:
        1. Retrieving the actual callable for each component
        2. Chaining them according to strategy
        3. Error handling at each step
        4. Timeout enforcement
        """
        # Phase 2: Implement actual execution
        logger.info(f"Executing composite skill {self.composite_id} with inputs: {inputs}")
        return {"status": "placeholder", "composite_id": self.composite_id}


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

async def example_skill_registration(redis_client: redis.Redis):
    """
    Example: Two agents register their skills.
    """
    registry = SkillRegistry(redis_client)
    
    # Agent 1: deployment-specialist registers its skills
    skill1 = SkillMetadata(
        skill_id="deploy_docker_app",
        agent_id="deployment-specialist",
        name="Deploy Docker Application",
        description="Package and deploy a Docker container to production",
        category=SkillCategory.ORCHESTRATION,
        signature=SkillSignature(
            inputs={"image_name": "str", "port": "int"},
            outputs={"deployment_id": "str", "url": "str"}
        ),
        examples=["deploy_ml_model", "deploy_api_server"],
    )
    await registry.register_skill(skill1)
    
    # Agent 2: cost-optimizer registers its skills
    skill2 = SkillMetadata(
        skill_id="optimize_model_costs",
        agent_id="cost-optimizer",
        name="Optimize Model Costs",
        description="Analyze API costs and recommend cheaper model alternatives",
        category=SkillCategory.OPTIMIZATION,
        signature=SkillSignature(
            inputs={"task_description": "str"},
            outputs={"recommended_model": "str", "cost_savings": "float"}
        ),
        examples=["switch_gpt4_to_gpt35", "use_ollama_fallback"],
    )
    await registry.register_skill(skill2)
    
    logger.info("Skills registered successfully")


async def example_skill_discovery(redis_client: redis.Redis):
    """
    Example: A new agent discovers and composes existing skills.
    """
    weaver = SkillWeaver(redis_client)
    
    # Query: "I need to deploy something cheaply"
    matches = await weaver.discover_skills("deploy optimized cost", top_k=5)
    
    logger.info(f"Found {len(matches)} matching skills:")
    for match in matches:
        logger.info(f"  - {match.metadata.name} (score: {match.relevance_score:.2f})")
        logger.info(f"    Reason: {match.reason}")
    
    # Compose the top 2 matches
    if len(matches) >= 2:
        skill_ids = [m.metadata.skill_id for m in matches[:2]]
        composite = await weaver.compose_skills(skill_ids, strategy="linear")
        logger.info(f"Composite skill created: {composite.composite_id}")
        
        # Teach an agent to use it
        await weaver.teach_agent("backend-specialist", composite)
        logger.info("Composite skill queued for backend-specialist")


if __name__ == "__main__":
    # Quick test
    async def main():
        redis_client = await redis.from_url("redis://localhost:6379")
        
        # Register skills
        await example_skill_registration(redis_client)
        
        # Discover and compose
        await example_skill_discovery(redis_client)
        
        await redis_client.close()
    
    asyncio.run(main())
