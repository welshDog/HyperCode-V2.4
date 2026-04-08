from typing import Dict, Any
from .models import TicketPayload, TicketType


def generate_json_payload(ticket: TicketPayload) -> Dict[str, Any]:
    fields: Dict[str, Any] = {
        "project": {"key": ticket.project_key},
        "summary": ticket.summary,
        "description": ticket.description,
        "issuetype": {"name": ticket.issue_type.value},
        "priority": {"name": ticket.priority},
    }
    if ticket.assignee:
        fields["assignee"] = {"name": ticket.assignee}
    if ticket.labels:
        fields["labels"] = ticket.labels
    if ticket.issue_type != TicketType.EPIC and ticket.epic_link:
        fields["customfield_10002"] = ticket.epic_link
    for k, v in ticket.custom_fields.items():
        fields[k] = v
    return {"fields": fields}


CSV_HEADERS = [
    "Project Key",
    "Summary",
    "Issue Type",
    "Description",
    "Priority",
    "Assignee",
    "Labels",
    "Epic Link",
]


def generate_csv_payload(ticket: TicketPayload) -> str:
    labels = ",".join(ticket.labels) if ticket.labels else ""
    assignee = ticket.assignee or ""
    epic_link = ticket.epic_link or ""
    row = [
        ticket.project_key,
        ticket.summary,
        ticket.issue_type.value,
        ticket.description,
        ticket.priority,
        assignee,
        labels,
        epic_link,
    ]
    escaped = []
    for cell in row:
        c = str(cell).replace("\n", " ")
        if any(ch in c for ch in [",", "\"", "\n"]):
            c = "\"" + c.replace("\"", "\"\"") + "\""
        escaped.append(c)
    return ",".join(escaped)
