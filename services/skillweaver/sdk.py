"""
SkillWeaver Agent SDK
====================

Easy integration for agents to use SkillWeaver.

Usage:
    from skillweaver_sdk import SkillWeaverClient, register_agent_skills
    
    client = SkillWeaverClient("http://skillweaver:8051")
    
    # Register skills on startup
    await register_agent_skills(client, "my-agent", [
        ("task_execution", "Execute core tasks", ...),
        ("api_integration", "Connect to APIs", ...),
    ])
    
    # Discover skills when handling novel tasks
    matches = await client.discover_skills("optimize costs")
    
    # Compose them
    composite = await client.compose_skills([m.skill_id for m in matches])
"""

import asyncio
import json
from typing import List, Dict, Any, Optional, Tuple

import httpx


class SkillWeaverClient:
    """Client for interacting with SkillWeaver server."""
    
    def __init__(self, base_url: str = "http://skillweaver:8051", timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy-load HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def health(self) -> dict:
        """Check SkillWeaver health."""
        client = await self._get_client()
        resp = await client.get(f"{self.base_url}/health")
        resp.raise_for_status()
        return resp.json()
    
    async def register_skill(
        self,
        skill_id: str,
        agent_id: str,
        name: str,
        description: str,
        category: str,
        inputs: Dict[str, str],
        outputs: Dict[str, str],
        timeout_seconds: float = 30.0,
        retry_count: int = 1,
        examples: List[str] = None,
        version: str = "1.0.0",
    ) -> dict:
        """Register a new skill."""
        client = await self._get_client()
        payload = {
            "skill_id": skill_id,
            "agent_id": agent_id,
            "name": name,
            "description": description,
            "category": category,
            "inputs": inputs,
            "outputs": outputs,
            "timeout_seconds": timeout_seconds,
            "retry_count": retry_count,
            "examples": examples or [],
            "version": version,
        }
        resp = await client.post(f"{self.base_url}/api/v1/skills/register", json=payload)
        resp.raise_for_status()
        return resp.json()
    
    async def discover_skills(
        self,
        query: str,
        category: Optional[str] = None,
        top_k: int = 5,
    ) -> List[dict]:
        """Discover relevant skills."""
        client = await self._get_client()
        payload = {
            "query": query,
            "category": category,
            "top_k": top_k,
        }
        resp = await client.post(f"{self.base_url}/api/v1/skills/discover", json=payload)
        resp.raise_for_status()
        return resp.json()
    
    async def compose_skills(
        self,
        skill_ids: List[str],
        strategy: str = "linear",
    ) -> dict:
        """Compose multiple skills."""
        client = await self._get_client()
        payload = {
            "skill_ids": skill_ids,
            "strategy": strategy,
        }
        resp = await client.post(f"{self.base_url}/api/v1/skills/compose", json=payload)
        resp.raise_for_status()
        return resp.json()
    
    async def list_skills(self, agent_id: Optional[str] = None) -> dict:
        """List registered skills."""
        client = await self._get_client()
        params = {}
        if agent_id:
            params["agent_id"] = agent_id
        resp = await client.get(f"{self.base_url}/api/v1/skills/list", params=params)
        resp.raise_for_status()
        return resp.json()
    
    async def composition_history(self, limit: int = 10) -> dict:
        """Get recent compositions."""
        client = await self._get_client()
        resp = await client.get(
            f"{self.base_url}/api/v1/compositions/history",
            params={"limit": limit}
        )
        resp.raise_for_status()
        return resp.json()
    
    async def stats(self) -> dict:
        """Get system statistics."""
        client = await self._get_client()
        resp = await client.get(f"{self.base_url}/api/v1/stats")
        resp.raise_for_status()
        return resp.json()


async def register_agent_skills(
    client: SkillWeaverClient,
    agent_id: str,
    skills: List[Tuple[str, str, str, Dict, Dict]],
) -> List[str]:
    """
    Register multiple skills for an agent.
    
    Args:
        client: SkillWeaverClient instance
        agent_id: The agent ID
        skills: List of (skill_id, name, description, inputs, outputs)
    
    Returns:
        List of registered skill IDs
    
    Example:
        await register_agent_skills(client, "backend-specialist", [
            ("deploy_docker", "Deploy Docker App", "...", {"image": "str"}, {"url": "str"}),
            ("api_call", "Call External API", "...", {"endpoint": "str"}, {"response": "dict"}),
        ])
    """
    registered = []
    for skill_id, name, description, inputs, outputs in skills:
        try:
            result = await client.register_skill(
                skill_id=skill_id,
                agent_id=agent_id,
                name=name,
                description=description,
                category="computation",  # Default, override as needed
                inputs=inputs,
                outputs=outputs,
            )
            registered.append(skill_id)
            print(f"✅ Registered skill: {name}")
        except Exception as e:
            print(f"❌ Failed to register {skill_id}: {e}")
    
    return registered


async def discover_and_compose(
    client: SkillWeaverClient,
    query: str,
    top_k: int = 3,
) -> Optional[str]:
    """
    Discover relevant skills and compose them.
    
    Args:
        client: SkillWeaverClient instance
        query: What you need (e.g., "optimize costs")
        top_k: Number of skills to use in composition
    
    Returns:
        Composite skill ID, or None if composition failed
    
    Example:
        composite_id = await discover_and_compose(client, "deploy with cost optimization")
    """
    # Discover
    matches = await client.discover_skills(query, top_k=top_k)
    
    if not matches:
        print(f"❌ No skills found for: {query}")
        return None
    
    print(f"✅ Found {len(matches)} relevant skills:")
    for match in matches:
        print(f"   - {match['name']} (score: {match['relevance_score']:.2f})")
    
    # Compose
    skill_ids = [m["skill_id"] for m in matches[:top_k]]
    composite = await client.compose_skills(skill_ids)
    
    print(f"✅ Composed into: {composite['composite_id']}")
    return composite["composite_id"]


# ============================================================================
# Example Usage
# ============================================================================

async def example_basic_usage():
    """Example: Basic SkillWeaver usage."""
    client = SkillWeaverClient("http://localhost:8051")
    
    try:
        # Check health
        health = await client.health()
        print(f"Health: {health['status']}")
        
        # Get stats
        stats = await client.stats()
        print(f"Total skills: {stats['total_skills']}")
        print(f"Total compositions: {stats['total_compositions']}")
        
    finally:
        await client.close()


async def example_register_and_discover():
    """Example: Register skills and discover them."""
    client = SkillWeaverClient("http://localhost:8051")
    
    try:
        # Register some example skills
        print("Registering skills...")
        await register_agent_skills(client, "backend-specialist", [
            (
                "deploy_docker",
                "Deploy Docker App",
                "Package and deploy a Docker container",
                {"image": "str", "port": "int"},
                {"deployment_id": "str", "url": "str"},
            ),
            (
                "optimize_costs",
                "Optimize Costs",
                "Analyze and reduce API costs",
                {"task": "str"},
                {"cost_savings": "float", "recommendation": "str"},
            ),
        ])
        
        # Discover relevant skills
        print("\nDiscovering skills...")
        composite = await discover_and_compose(client, "deploy something cheaply")
        
        # Get composition history
        print("\nRecent compositions:")
        history = await client.composition_history(limit=5)
        for comp in history["compositions"]:
            print(f"  - {comp['composite_id']}: {comp['component_skills']}")
        
    finally:
        await client.close()


if __name__ == "__main__":
    print("=== Basic Usage ===")
    asyncio.run(example_basic_usage())
    
    print("\n=== Register & Discover ===")
    asyncio.run(example_register_and_discover())
