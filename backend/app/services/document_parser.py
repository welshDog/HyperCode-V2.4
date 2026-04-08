"""
document_parser.py — Ingests various document types and extracts structured
requirements via the Brain LLM chain (Ollama → Perplexity → OpenRouter).
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict

from app.agents.brain import brain
from app.schemas.planning import (
    DocumentInput,
    DocumentType,
    ExtractedRequirement,
    ParsedDocument,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Keyword-based document type classifier
# ---------------------------------------------------------------------------

_PRD_KEYWORDS = {
    "acceptance criteria", "user story", "as a user", "product requirement",
    "feature request", "epics", "sprint", "roadmap",
}
_ISSUE_KEYWORDS = {
    "bug", "steps to reproduce", "expected behavior", "actual behavior",
    "reproduction", "stacktrace", "stack trace", "error log", "regression",
}
_DESIGN_KEYWORDS = {
    "architecture", "component", "diagram", "sequence", "entity relationship",
    "data flow", "api contract", "schema design", "system design",
    "infrastructure", "deployment topology",
}


def detect_document_type(content: str) -> DocumentType:
    """
    Keyword-based document type classifier.

    Scoring: each matched keyword in the content votes for its category.
    The highest-scoring category wins; ties fall back to GENERIC.
    """
    lower = content.lower()
    scores: Dict[DocumentType, int] = {
        DocumentType.PRD: 0,
        DocumentType.ISSUE: 0,
        DocumentType.DESIGN: 0,
    }

    for kw in _PRD_KEYWORDS:
        if kw in lower:
            scores[DocumentType.PRD] += 1

    for kw in _ISSUE_KEYWORDS:
        if kw in lower:
            scores[DocumentType.ISSUE] += 1

    for kw in _DESIGN_KEYWORDS:
        if kw in lower:
            scores[DocumentType.DESIGN] += 1

    best_type = max(scores, key=lambda k: scores[k])
    best_score = scores[best_type]

    if best_score == 0:
        return DocumentType.GENERIC

    # Require at least 2 keyword matches for non-generic classification
    if best_score < 2:
        return DocumentType.GENERIC

    return best_type


# ---------------------------------------------------------------------------
# Prompt templates per document type
# ---------------------------------------------------------------------------

_BASE_INSTRUCTION = """
You are a senior engineering analyst.  Extract structured requirements from the
document below.  Output ONLY valid JSON — no prose, no markdown fences.

JSON schema:
{{
  "requirements": [
    {{
      "title": "<short headline>",
      "description": "<full requirement description>",
      "acceptance_criteria": ["<criterion 1>", "<criterion 2>"],
      "technical_constraints": ["<constraint 1>"],
      "dependencies": ["<dependency 1>"]
    }}
  ]
}}

Rules:
- Do NOT invent requirements not present in the document.
- acceptance_criteria must be testable conditions.
- technical_constraints cover tech stack, performance, or compatibility limits.
- dependencies name other requirements or external systems.
- Omit empty lists.
"""

_TYPE_HINTS: Dict[DocumentType, str] = {
    DocumentType.ISSUE: (
        "This is a BUG REPORT.  Focus on: bug description, reproduction steps, "
        "expected vs actual behaviour, and the fix acceptance criteria."
    ),
    DocumentType.PRD: (
        "This is a PRODUCT REQUIREMENTS DOCUMENT.  Focus on: user stories, "
        "feature descriptions, success metrics, and acceptance criteria."
    ),
    DocumentType.DESIGN: (
        "This is a TECHNICAL DESIGN DOCUMENT.  Focus on: components, interfaces, "
        "data flows, API contracts, and non-functional requirements."
    ),
    DocumentType.GENERIC: (
        "Extract all identifiable functional and non-functional requirements."
    ),
}


def _build_extraction_prompt(content: str, doc_type: DocumentType) -> str:
    type_hint = _TYPE_HINTS.get(doc_type, _TYPE_HINTS[DocumentType.GENERIC])
    return (
        f"{_BASE_INSTRUCTION}\n\nDocument type context: {type_hint}\n\n"
        f"--- DOCUMENT START ---\n{content}\n--- DOCUMENT END ---"
    )


# ---------------------------------------------------------------------------
# DocumentParser
# ---------------------------------------------------------------------------

class DocumentParser:
    """
    Parses an incoming DocumentInput into a ParsedDocument by:
      1. Auto-detecting the document type (unless already specified).
      2. Selecting the appropriate prompt template.
      3. Calling the Brain LLM chain for extraction.
      4. Parsing the LLM JSON response into ExtractedRequirement objects.
    """

    async def parse(self, doc_input: DocumentInput) -> ParsedDocument:
        """
        Main entry point.  Accepts a DocumentInput and returns a ParsedDocument.
        """
        # 1. Determine document type
        if doc_input.document_type == DocumentType.GENERIC:
            detected_type = detect_document_type(doc_input.content)
            logger.info(f"[PARSER] Auto-detected document type: {detected_type}")
        else:
            detected_type = doc_input.document_type
            logger.info(f"[PARSER] Using provided document type: {detected_type}")

        # 2. Build extraction prompt
        prompt = _build_extraction_prompt(doc_input.content, detected_type)

        # 3. Call Brain (Ollama → Perplexity → OpenRouter fallback chain)
        raw_response = await brain.think(
            role="Requirements Extraction Specialist",
            task_description=prompt,
            use_memory=False,
        )

        # 4. Parse JSON response
        requirements = self._parse_llm_response(raw_response)

        return ParsedDocument(
            requirements=requirements,
            source_metadata=doc_input.metadata or {},
            detected_document_type=detected_type,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_llm_response(self, raw: str) -> list[ExtractedRequirement]:
        """Extract ExtractedRequirement objects from the LLM's JSON output."""
        try:
            # Strip any accidental markdown fences
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(
                    line for line in lines
                    if not line.startswith("```")
                ).strip()

            data: Dict[str, Any] = json.loads(cleaned)
            raw_reqs = data.get("requirements", [])
            requirements = []
            for r in raw_reqs:
                requirements.append(
                    ExtractedRequirement(
                        title=r.get("title", "Untitled"),
                        description=r.get("description", ""),
                        acceptance_criteria=r.get("acceptance_criteria", []),
                        technical_constraints=r.get("technical_constraints", []),
                        dependencies=r.get("dependencies", []),
                    )
                )
            logger.info(f"[PARSER] Extracted {len(requirements)} requirement(s).")
            return requirements
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.warning(
                f"[PARSER] Failed to parse LLM JSON response: {exc}.  "
                "Falling back to single generic requirement."
            )
            return [
                ExtractedRequirement(
                    title="Unparsed Document Content",
                    description=raw[:2000],
                    acceptance_criteria=[],
                    technical_constraints=[],
                    dependencies=[],
                )
            ]


# Global instance
document_parser = DocumentParser()
