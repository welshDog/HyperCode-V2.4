from .models import TicketPayload, TicketType


def template_agent_registry_story(project_key: str) -> TicketPayload:
    return TicketPayload(
        project_key=project_key,
        summary="Agent Registry v1: Postgres persistence and SSE watch",
        description=(
            "Implement registry backed by Postgres with idempotent register/update, "
            "immutable role/ID, semver versioning, and SSE /agents/watch with ≤500 ms latency."
        ),
        issue_type=TicketType.STORY,
        priority="High",
        labels=["registry", "agents", "sse"],
        custom_fields={"Acceptance Criteria": "See story details"},
    )


def template_event_bus_task(project_key: str) -> TicketPayload:
    return TicketPayload(
        project_key=project_key,
        summary="Event Bus hardening: at-least-once, dedup, ACLs, circuit breaker",
        description=(
            "Add dedup with TTL, topic ACLs, and publisher pause after 3 failed health checks; "
            "validate zero duplicates across 10k events."
        ),
        issue_type=TicketType.TASK,
        priority="High",
        labels=["event-bus", "acl", "reliability"],
    )


def template_architect_epic(project_key: str) -> TicketPayload:
    return TicketPayload(
        project_key=project_key,
        summary="Architect Agent v0.1",
        description=(
            "NestJS microservice with lifecycle, health/version endpoints, subscribes to domain.design.request "
            "and publishes domain.design.completed with schema validation."
        ),
        issue_type=TicketType.EPIC,
        priority="Medium",
        labels=["architect", "agent"],
    )


def template_bug_example(project_key: str) -> TicketPayload:
    return TicketPayload(
        project_key=project_key,
        summary="SSE watch stream returns 500 under load",
        description="Investigate and fix SSE stream stability; ensure compatible Starlette/FastAPI versions.",
        issue_type=TicketType.BUG,
        priority="High",
        labels=["sse", "bug"],
    )


TEMPLATES = {
    "agent-registry-story": template_agent_registry_story,
    "event-bus-task": template_event_bus_task,
    "architect-epic": template_architect_epic,
    "bug-example": template_bug_example,
}
