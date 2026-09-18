from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple


VALID_CATEGORIES = {
    "computation",
    "io",
    "orchestration",
    "optimization",
    "safety",
    "communication",
    "learning",
    "testing",
}

_SKILL_ID_RE = re.compile(r"^[a-z0-9_]{3,64}$")
_REQUIRED_KEYS = ("skill_id", "name", "description", "category", "inputs", "outputs")


BACKEND_SPECIALIST_SKILLS: List[Dict[str, Any]] = [
    {
        "skill_id": "execute_backend_plan",
        "name": "Execute Backend Plan with Approvals",
        "description": (
            "Orchestrate a backend task end-to-end: retrieve RAG context, "
            "merge project memory state, generate LLM implementation plan, "
            "request approval when required, then execute plan steps against "
            "the codebase (FastAPI route creation, DB schema updates, etc.)."
        ),
        "category": "orchestration",
        "inputs": {
            "task": "str",
            "context": "dict",
            "requires_approval": "bool",
        },
        "outputs": {
            "status": "str",
            "plan": "str",
            "artifacts": "list[str]",
        },
        "timeout_seconds": 300,
        "examples": [
            "build a /users CRUD API endpoint",
            "implement a hello world route with timestamp",
        ],
        "version": "1.0.0",
    },
    {
        "skill_id": "generate_api_endpoint",
        "name": "Generate FastAPI Route / Endpoint",
        "description": (
            "Create a FastAPI APIRouter file with Pydantic models, path "
            "operations, and idiomatic response shapes. Registers routes in "
            "api/routes/ so the backend app can mount them. Concrete "
            "production-style handlers for hello, user-profile, and similar."
        ),
        "category": "io",
        "inputs": {
            "route_path": "str",
            "methods": "list[str]",
            "input_schema": "dict",
            "output_schema": "dict",
        },
        "outputs": {
            "file_path": "str",
            "router_definition": "str",
            "endpoints": "list[str]",
        },
        "timeout_seconds": 90,
        "examples": [
            "hello endpoint GET /hello returning timestamp",
            "user profile endpoint GET /user/{user_id} with Pydantic model",
        ],
        "version": "1.0.0",
    },
    {
        "skill_id": "database_schema_plan",
        "name": "Database Schema and DDL Planning",
        "description": (
            "Produce PostgreSQL / ANSI-SQL schema plans, DDL statements, "
            "index recommendations, and migration shapes. Maps to the backend "
            "specialist's LLM chain that generates database-safe code paths "
            "with pydantic models and typed query parameters."
        ),
        "category": "computation",
        "inputs": {
            "entities": "list[dict]",
            "relationships": "list[dict]",
            "dialect": "str",
        },
        "outputs": {
            "ddl_statements": "list[str]",
            "pydantic_models": "list[str]",
            "indexes": "list[str]",
        },
        "timeout_seconds": 120,
        "examples": [
            "plan a users + enrollments schema with foreign keys",
            "produce migration for User(id,name,email,avatar_url)",
        ],
        "version": "1.0.0",
    },
    {
        "skill_id": "business_logic_generation",
        "name": "Business Logic Service Layer Generation",
        "description": (
            "Write service-layer business logic: input validation, rule "
            "evaluation, transformation pipelines, and error handling. "
            "Integrates with the approval system so high-risk steps can be "
            "reviewed by a human before committing."
        ),
        "category": "computation",
        "inputs": {
            "rules": "list[dict]",
            "input_shape": "dict",
            "output_shape": "dict",
        },
        "outputs": {
            "service_function": "str",
            "unit_tests": "list[str]",
            "risk_flags": "list[str]",
        },
        "timeout_seconds": 180,
        "examples": [
            "write a discount service that applies tiered rules",
            "build an order-validator with 3 product checks",
        ],
        "version": "1.0.0",
    },
    {
        "skill_id": "llm_implementation_plan",
        "name": "LLM-Backed Implementation Plan (Anthropic / Ollama)",
        "description": (
            "Consult the HyperCode LLM chain (Anthropic AsyncAnthropic first, "
            "Ollama AsyncOpenAI-compat fallback on :11434/v1 second) to "
            "produce a step-by-step backend implementation plan. Includes "
            "RAG context injection and project memory state so the plan is "
            "tailored to the real codebase, not generic docs."
        ),
        "category": "learning",
        "inputs": {
            "task": "str",
            "rag_context": "str",
            "project_context": "dict",
            "max_tokens": "int",
        },
        "outputs": {
            "plan_text": "str",
            "model_used": "str",
            "fallback_triggered": "bool",
        },
        "timeout_seconds": 240,
        "examples": [
            "create an implementation plan for the checkout flow",
            "plan authentication endpoints with Supabase JWT",
        ],
        "version": "1.0.0",
    },
    {
        "skill_id": "quality_gate_validation",
        "name": "Quality Gate and Approval Validation",
        "description": (
            "Run the backend specialist's built-in approval system against "
            "a task + plan payload. Returns approved/rejected with optional "
            "human-driven modifications, enforces 300s timeout, and logs "
            "audit lines via the structlog/stdlog adapter. Covers task "
            "validation (task/description presence, 422s, etc.)."
        ),
        "category": "testing",
        "inputs": {
            "action": "str",
            "payload": "dict",
            "timeout_seconds": "int",
        },
        "outputs": {
            "status": "str",
            "modifications": "str | null",
            "reason": "str | null",
        },
        "timeout_seconds": 300,
        "examples": [
            "approve an implement_feature action with plan attached",
            "validate payload shape of a /execute TaskRequest",
        ],
        "version": "1.0.0",
    },
]


def validate_skill_entry(skill: Dict[str, Any]) -> List[str]:
    errors: List[str] = []

    if not isinstance(skill, dict):
        return ["skill entry must be a dict"]

    for key in _REQUIRED_KEYS:
        if key not in skill:
            errors.append(f"missing required key: {key}")
        elif isinstance(skill[key], str) and not skill[key].strip():
            errors.append(f"required key {key!r} is empty")

    if "skill_id" in skill:
        sid = skill["skill_id"]
        if not isinstance(sid, str) or not _SKILL_ID_RE.match(sid):
            errors.append(
                "skill_id must match [a-z0-9_] length 3-64, got "
                f"{sid!r}"
            )

    if "category" in skill:
        cat = skill["category"]
        if not isinstance(cat, str) or cat not in VALID_CATEGORIES:
            errors.append(
                f"invalid category {cat!r}; must be one of "
                f"{sorted(VALID_CATEGORIES)}"
            )

    for io_key in ("inputs", "outputs"):
        if io_key not in skill:
            continue
        io_val = skill[io_key]
        if not isinstance(io_val, dict):
            errors.append(f"{io_key} must be dict[str,str], got non-dict")
            continue
        for k, v in io_val.items():
            if not isinstance(k, str):
                errors.append(f"{io_key} key {k!r} is not str")
            if not isinstance(v, str):
                errors.append(
                    f"{io_key}[{k!r}] value type hint must be str, "
                    f"got {type(v).__name__}"
                )

    return errors


def curate_skills_for_registration(
    skills: List[Dict[str, Any]],
    logger: Any,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    valid_batch: List[Dict[str, Any]] = []
    dropped_invalid: List[Dict[str, Any]] = []

    for skill in skills:
        sid = skill.get("skill_id") if isinstance(skill, dict) else None
        reasons = validate_skill_entry(skill)
        if reasons:
            dropped = {"skill_id": sid, "reasons": reasons, "entry": skill}
            dropped_invalid.append(dropped)
            if logger is not None:
                try:
                    logger.warning(
                        "skillweaver_skill_invalid",
                        skill_id=sid,
                        reasons=reasons,
                    )
                except Exception:
                    pass
            continue
        valid_batch.append(skill)

    if skills and not valid_batch and logger is not None:
        try:
            logger.warning(
                "skillweaver_all_skills_invalid",
                total_input=len(skills),
            )
        except Exception:
            pass

    return valid_batch, dropped_invalid


__all__ = [
    "VALID_CATEGORIES",
    "BACKEND_SPECIALIST_SKILLS",
    "validate_skill_entry",
    "curate_skills_for_registration",
]
