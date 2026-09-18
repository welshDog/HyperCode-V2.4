"""
SkillWeaver: Cross-Agent Skill Synthesis Engine
==============================================

Phase 1 of HyperCode Autonomous Learning System (ALS).

Enables agents to:
- Register their skills
- Discover skills from other agents
- Compose skills into new capabilities
- Execute composite skills at runtime

All without re-coding or re-deployment.
"""

from .skillweaver import (
    SkillWeaver,
    SkillRegistry,
    SkillMetadata,
    SkillSignature,
    SkillCategory,
    SkillMatch,
    CompositeSkill,
)

__version__ = "1.0.0"
__all__ = [
    "SkillWeaver",
    "SkillRegistry",
    "SkillMetadata",
    "SkillSignature",
    "SkillCategory",
    "SkillMatch",
    "CompositeSkill",
]
