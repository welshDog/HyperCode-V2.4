from typing import List
from .models import TicketPayload, TicketType


REQUIRED_FIELDS = {
    TicketType.BUG: ["project_key", "summary", "description", "priority"],
    TicketType.STORY: ["project_key", "summary", "description", "priority"],
    TicketType.TASK: ["project_key", "summary", "description", "priority"],
    TicketType.EPIC: ["project_key", "summary", "description"],
}


def validate_ticket(ticket: TicketPayload) -> List[str]:
    errors: List[str] = []
    fields = REQUIRED_FIELDS.get(ticket.issue_type, [])
    for f in fields:
        if getattr(ticket, f) in (None, ""):
            errors.append(f"Missing required field: {f}")
    if ticket.issue_type == TicketType.EPIC and ticket.epic_link:
        errors.append("Epic issues should not have epic_link")
    return errors
