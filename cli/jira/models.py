from enum import Enum
from typing import List, Optional, Dict, Any


class TicketType(str, Enum):
    BUG = "Bug"
    STORY = "Story"
    TASK = "Task"
    EPIC = "Epic"


class TicketPayload:
    def __init__(
        self,
        project_key: str,
        summary: str,
        description: str,
        issue_type: TicketType,
        priority: str,
        assignee: Optional[str] = None,
        labels: Optional[List[str]] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
        epic_link: Optional[str] = None,
    ):
        self.project_key = project_key
        self.summary = summary
        self.description = description
        self.issue_type = issue_type
        self.priority = priority
        self.assignee = assignee
        self.labels = labels or []
        self.custom_fields = custom_fields or {}
        self.epic_link = epic_link
