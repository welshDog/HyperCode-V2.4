"""
SkillWeaver Integration Tests
=============================

Tests to verify SkillWeaver is working correctly.

Run with: pytest tests/test_skillweaver.py -v
"""

import asyncio
import pytest
import redis.asyncio as redis

from services.skillweaver.skillweaver import (
    SkillWeaver,
    SkillRegistry,
    SkillMetadata,
    SkillSignature,
    SkillCategory,
)


@pytest.fixture
async def redis_client():
    """Create a test Redis client."""
    import os
    redis_url = os.getenv("TEST_REDIS_URL", "redis://localhost:6379/15")
    client = await redis.from_url(redis_url)
    await client.flushdb()
    yield client
    await client.aclose()


@pytest.mark.asyncio
async def test_skill_registration(redis_client):
    """Test registering a skill."""
    registry = SkillRegistry(redis_client)
    
    skill = SkillMetadata(
        skill_id="test_skill_001",
        agent_id="test_agent",
        name="Test Skill",
        description="A test skill",
        category=SkillCategory.COMPUTATION,
        signature=SkillSignature(
            inputs={"input": "str"},
            outputs={"output": "str"}
        ),
    )
    
    await registry.register_skill(skill)
    
    # Verify it was registered
    retrieved = await registry.get_skill("test_skill_001")
    assert retrieved is not None
    assert retrieved.name == "Test Skill"
    assert retrieved.agent_id == "test_agent"


@pytest.mark.asyncio
async def test_skill_discovery(redis_client):
    """Test discovering skills."""
    registry = SkillRegistry(redis_client)
    
    # Register test skills
    for i in range(3):
        skill = SkillMetadata(
            skill_id=f"deploy_skill_{i}",
            agent_id=f"agent_{i}",
            name=f"Deploy Service {i}",
            description="Deploy a service to production",
            category=SkillCategory.ORCHESTRATION,
            signature=SkillSignature(
                inputs={"service": "str"},
                outputs={"deployed": "bool"}
            ),
        )
        await registry.register_skill(skill)
    
    weaver = SkillWeaver(redis_client)
    
    # Discover deployment-related skills
    matches = await weaver.discover_skills("deploy", top_k=5)
    
    assert len(matches) == 3
    assert all(m.relevance_score > 0 for m in matches)


@pytest.mark.asyncio
async def test_skill_composition_validation(redis_client):
    """Test validating skill composition."""
    weaver = SkillWeaver(redis_client)
    
    # Empty list should be invalid
    valid, reason = await weaver.validate_composition([])
    assert not valid
    
    # Too many skills should be invalid
    valid, reason = await weaver.validate_composition(["s1"] * 15)
    assert not valid
    
    # Non-existent skill should be invalid
    valid, reason = await weaver.validate_composition(["nonexistent"])
    assert not valid


@pytest.mark.asyncio
async def test_skill_composition_creation(redis_client):
    """Test creating a composite skill."""
    registry = SkillRegistry(redis_client)
    
    # Register test skills
    skill1 = SkillMetadata(
        skill_id="skill_a",
        agent_id="agent_1",
        name="Skill A",
        description="First skill",
        category=SkillCategory.COMPUTATION,
        signature=SkillSignature(
            inputs={"x": "int"},
            outputs={"result": "int"}
        ),
    )
    await registry.register_skill(skill1)
    
    skill2 = SkillMetadata(
        skill_id="skill_b",
        agent_id="agent_2",
        name="Skill B",
        description="Second skill",
        category=SkillCategory.OPTIMIZATION,
        signature=SkillSignature(
            inputs={"y": "int"},
            outputs={"optimized": "int"}
        ),
    )
    await registry.register_skill(skill2)
    
    weaver = SkillWeaver(redis_client)
    
    # Compose them
    composite = await weaver.compose_skills(
        skill_ids=["skill_a", "skill_b"],
        strategy="linear"
    )
    
    assert composite.composite_id is not None
    assert len(composite.component_skills) == 2
    assert composite.strategy == "linear"


@pytest.mark.asyncio
async def test_multiple_agents_skills(redis_client):
    """Test multiple agents registering different skills."""
    registry = SkillRegistry(redis_client)
    
    # Agent 1: deployment specialist
    deploy_skill = SkillMetadata(
        skill_id="deploy_docker",
        agent_id="deploy-specialist",
        name="Deploy Docker",
        description="Deploy containers",
        category=SkillCategory.ORCHESTRATION,
        signature=SkillSignature(
            inputs={"image": "str"},
            outputs={"url": "str"}
        ),
    )
    await registry.register_skill(deploy_skill)
    
    # Agent 2: cost optimizer
    cost_skill = SkillMetadata(
        skill_id="optimize_cost",
        agent_id="cost-optimizer",
        name="Optimize Cost",
        description="Reduce costs",
        category=SkillCategory.OPTIMIZATION,
        signature=SkillSignature(
            inputs={"task": "str"},
            outputs={"savings": "float"}
        ),
    )
    await registry.register_skill(cost_skill)
    
    # Agent 3: quality checker
    quality_skill = SkillMetadata(
        skill_id="check_quality",
        agent_id="quality-checker",
        name="Check Quality",
        description="Verify quality",
        category=SkillCategory.TESTING,
        signature=SkillSignature(
            inputs={"result": "dict"},
            outputs={"quality_score": "float"}
        ),
    )
    await registry.register_skill(quality_skill)
    
    # Each agent can list its skills
    deploy_skills = await registry.list_skills_by_agent("deploy-specialist")
    assert len(deploy_skills) == 1
    assert deploy_skills[0].skill_id == "deploy_docker"
    
    cost_skills = await registry.list_skills_by_agent("cost-optimizer")
    assert len(cost_skills) == 1
    
    quality_skills = await registry.list_skills_by_agent("quality-checker")
    assert len(quality_skills) == 1


@pytest.mark.asyncio
async def test_skill_category_filtering(redis_client):
    """Test filtering skills by category."""
    registry = SkillRegistry(redis_client)
    weaver = SkillWeaver(redis_client)
    
    # Register skills in different categories
    for category in [SkillCategory.COMPUTATION, SkillCategory.IO, SkillCategory.OPTIMIZATION]:
        skill = SkillMetadata(
            skill_id=f"skill_{category.value}",
            agent_id="test_agent",
            name=f"Skill {category.value}",
            description=f"A {category.value} skill",
            category=category,
            signature=SkillSignature(
                inputs={"x": "str"},
                outputs={"y": "str"}
            ),
        )
        await registry.register_skill(skill)
    
    # Filter by category
    opt_skills = await registry.list_skills_by_category(SkillCategory.OPTIMIZATION)
    assert len(opt_skills) == 1
    assert opt_skills[0].skill_id == "skill_optimization"


@pytest.mark.asyncio
async def test_discover_with_category_filter(redis_client):
    """Test discovery with category filtering."""
    registry = SkillRegistry(redis_client)
    
    # Register skills
    for i in range(3):
        skill = SkillMetadata(
            skill_id=f"opt_skill_{i}",
            agent_id="agent",
            name=f"Optimize {i}",
            description="Optimization skill",
            category=SkillCategory.OPTIMIZATION,
            signature=SkillSignature(inputs={"x": "str"}, outputs={"y": "str"}),
        )
        await registry.register_skill(skill)
    
    weaver = SkillWeaver(redis_client)
    
    # Discover with category filter
    matches = await weaver.discover_skills(
        query="optimize",
        category=SkillCategory.OPTIMIZATION,
        top_k=5
    )
    
    assert len(matches) == 3
    assert all(m.metadata.category == SkillCategory.OPTIMIZATION for m in matches)


@pytest.mark.asyncio
async def test_skill_versioning(redis_client):
    """Test skill versioning."""
    registry = SkillRegistry(redis_client)
    
    skill_v1 = SkillMetadata(
        skill_id="versioned_skill",
        agent_id="agent",
        name="My Skill",
        description="A versioned skill",
        category=SkillCategory.COMPUTATION,
        signature=SkillSignature(inputs={"x": "int"}, outputs={"y": "int"}),
        version="1.0.0",
    )
    await registry.register_skill(skill_v1)
    
    retrieved = await registry.get_skill("versioned_skill")
    assert retrieved.version == "1.0.0"


if __name__ == "__main__":
    # Run with pytest
    # pytest services/skillweaver/tests.py -v
    print("Run tests with: pytest services/skillweaver/tests.py -v")
