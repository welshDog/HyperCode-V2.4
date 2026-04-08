from cli.jira.models import TicketPayload, TicketType
from cli.jira.generator import generate_csv_payload, generate_json_payload
from cli.jira.validator import validate_ticket


def test_json_generation_story():
    t = TicketPayload(
        project_key="HC",
        summary="Story",
        description="Desc",
        issue_type=TicketType.STORY,
        priority="High",
        labels=["x"],
        assignee="alice",
        epic_link="EPIC-1",
    )
    payload = generate_json_payload(t)
    assert payload["fields"]["project"]["key"] == "HC"
    assert payload["fields"]["issuetype"]["name"] == "Story"
    assert payload["fields"]["priority"]["name"] == "High"


def test_csv_generation():
    t = TicketPayload(
        project_key="HC",
        summary="Example, with comma",
        description="Line with, comma",
        issue_type=TicketType.BUG,
        priority="Medium",
        labels=["a", "b"],
    )
    line = generate_csv_payload(t)
    assert line.startswith("HC,")
    assert '"Example, with comma"' in line


def test_validation_required_fields():
    t = TicketPayload(
        project_key="",
        summary="",
        description="",
        issue_type=TicketType.TASK,
        priority="",
    )
    errors = validate_ticket(t)
    assert len(errors) >= 1
