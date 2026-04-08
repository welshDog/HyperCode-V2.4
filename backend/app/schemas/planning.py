"""planning.py — Pydantic schemas for the HyperCode planning system."""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DocumentType(str, Enum):
    ISSUE = "issue"
    PRD = "prd"
    DESIGN = "design"
    GENERIC = "generic"


class FileChangeType(str, Enum):
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"


# ---------------------------------------------------------------------------
# Input schemas
# ---------------------------------------------------------------------------

class DocumentInput(BaseModel):
    """Raw document fed into the planning pipeline."""
    content: str = Field(..., description="Full text content of the document.")
    document_type: DocumentType = Field(
        default=DocumentType.GENERIC,
        description="Hint about the document's origin/format.",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Arbitrary key-value pairs (task_id, author, source_url, …).",
    )


# ---------------------------------------------------------------------------
# Extracted requirement schemas
# ---------------------------------------------------------------------------

class ExtractedRequirement(BaseModel):
    """A single structured requirement parsed out of a document."""
    title: str = Field(..., description="Short requirement headline.")
    description: str = Field(..., description="Full requirement description.")
    acceptance_criteria: List[str] = Field(
        default_factory=list,
        description="Testable conditions that confirm the requirement is met.",
    )
    technical_constraints: List[str] = Field(
        default_factory=list,
        description="Technology, performance, or compatibility constraints.",
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="Other requirements or systems this one relies on.",
    )


class ParsedDocument(BaseModel):
    """Output of DocumentParser — a list of structured requirements + source metadata."""
    requirements: List[ExtractedRequirement] = Field(
        default_factory=list,
        description="All requirements extracted from the source document.",
    )
    source_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Preserved metadata from the original DocumentInput.",
    )
    detected_document_type: DocumentType = Field(
        default=DocumentType.GENERIC,
        description="Document type as detected or confirmed by the parser.",
    )


# ---------------------------------------------------------------------------
# Plan schemas
# ---------------------------------------------------------------------------

class PlanPhase(BaseModel):
    """A single phase in the generated coding plan.  High-level objectives first."""
    phase_number: int = Field(..., description="1-based sequential phase index.")
    title: str = Field(..., description="Short phase title (e.g. 'Data Layer Setup').")
    description: str = Field(
        ...,
        description=(
            "High-level objective for this phase.  "
            "Must focus on intent and rationale — not file-by-file steps."
        ),
    )
    workflow_steps: List[str] = Field(
        default_factory=list,
        description="Ordered list of logical steps to achieve the phase objective.",
    )


class FileChange(BaseModel):
    """A single file-level change recommended by the plan."""
    file_path: str = Field(..., description="Relative path from repo root.")
    change_type: FileChangeType = Field(..., description="create | modify | delete")
    description: str = Field(..., description="What changes and why (one sentence).")
    rationale: str = Field(
        ...,
        description="Why this change is necessary in the context of the overall plan.",
    )


class CodingPlan(BaseModel):
    """
    Full structured coding plan produced by PlanGenerator.

    Output order:
      1. summary          — executive overview
      2. phases           — phased objectives (no file-level detail inside phases)
      3. file_changes_summary — file-level section (separate from phases)
      4. follow_up_instructions — optional agent handoff notes
    """
    summary: str = Field(
        ...,
        description="Brief executive summary of the overall plan and its goals.",
    )
    phases: List[PlanPhase] = Field(
        default_factory=list,
        description=(
            "Ordered phases.  Each phase describes a cohesive objective.  "
            "File-level details live in file_changes_summary, not here."
        ),
    )
    file_changes_summary: List[FileChange] = Field(
        default_factory=list,
        description="All file-level changes consolidated in one section.",
    )
    follow_up_instructions: Optional[str] = Field(
        default=None,
        description="Instructions for downstream agents after plan execution.",
    )
