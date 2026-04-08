import logging
import json
import re
from app.agents.brain import brain
from app.core.storage import get_storage
from datetime import datetime

logger = logging.getLogger(__name__)


class ArchitectAgent:
    """
    The Architect: Orchestrates a multi-agent workflow to build software.
    Acts as the 'Planner' and 'Manager' described in the Research Report.

    On completion, automatically writes a handoff note to the Router's
    inbox so the next agent in the pipeline has context without manual
    wiring.
    """

    def __init__(self):
        self.role = "System Architect"

    async def process(
        self,
        goal: str,
        context: dict = None,
        conversation_id: str | None = None,
    ) -> str:
        """
        Executes the Multi-Agent Workflow: Plan -> Code -> Review.
        Auto-writes a handoff note to the router on completion.
        """
        logger.info(f"[{self.role}] Initializing Swarm for goal: {goal}")

        # ------------------------------------------------------------------
        # 1. PLANNER AGENT
        # ------------------------------------------------------------------
        logger.info(f"[{self.role}] Phase 1: Planning...")
        plan_prompt = (
            f"Act as a Senior Software Architect. "
            f"Goal: {goal}\n"
            f"Create a detailed, step-by-step implementation plan. "
            f"Return ONLY a JSON array of steps, where each step has "
            f"a 'title' and 'description'."
        )
        plan_json_str = await brain.think(
            "Planner Agent",
            plan_prompt,
            conversation_id=conversation_id,
            agent_id="architect",
            memory_mode="shared" if conversation_id else "none",
        )

        try:
            clean_json = plan_json_str.replace("```json", "").replace("```", "").strip()
            steps = json.loads(clean_json)
        except Exception:
            logger.warning(f"[{self.role}] Failed to parse JSON plan. Using raw text fallback.")
            steps = [{"title": "Execute Goal", "description": goal}]

        # ------------------------------------------------------------------
        # 2. CODER AGENT
        # ------------------------------------------------------------------
        logger.info(f"[{self.role}] Phase 2: Coding...")
        code_artifacts = []

        for i, step in enumerate(steps):
            step_title = step.get("title", f"Step {i + 1}")
            step_desc = step.get("description", "")

            logger.info(f"[{self.role}] executing step {i + 1}: {step_title}")

            code_prompt = (
                f"Act as a Senior Python Developer. "
                f"Task: {step_title}\n"
                f"Description: {step_desc}\n"
                f"Context: We are building '{goal}'.\n"
                f"Write the necessary code. Include comments. Return ONLY the code."
            )
            code = await brain.think(
                "Coder Agent",
                code_prompt,
                conversation_id=conversation_id,
                agent_id="architect",
                memory_mode="shared" if conversation_id else "none",
            )
            code_artifacts.append(f"### Step {i + 1}: {step_title}\n\n```python\n{code}\n```")

        # ------------------------------------------------------------------
        # 3. REVIEWER AGENT
        # ------------------------------------------------------------------
        logger.info(f"[{self.role}] Phase 3: Reviewing...")
        full_code = "\n".join(code_artifacts)
        review_prompt = (
            f"Act as a QA Security Engineer. "
            f"Review the following code for security vulnerabilities and best practices:\n"
            f"{full_code}\n"
            f"Provide a summary of issues and a 'Pass/Fail' grade."
        )
        review = await brain.think(
            "Reviewer Agent",
            review_prompt,
            conversation_id=conversation_id,
            agent_id="architect",
            memory_mode="shared" if conversation_id else "none",
        )

        # ------------------------------------------------------------------
        # 4. COMPILE REPORT
        # ------------------------------------------------------------------
        final_report = (
            f"# 🏗️ Multi-Agent Build Report: {goal}\n\n"
            f"## 1. Architecture Plan\n"
            f"{json.dumps(steps, indent=2)}\n\n"
            f"## 2. Implementation\n"
            f"{full_code}\n\n"
            f"## 3. Security Review\n"
            f"{review}\n"
        )

        # ------------------------------------------------------------------
        # 5. ARCHIVE to MinIO
        # ------------------------------------------------------------------
        storage = get_storage()
        task_id = (context or {}).get("task_id")

        if task_id:
            filename = f"build_{task_id}.md"
            metadata = {
                "agent": self.role,
                "goal": goal,
                "created_at": datetime.utcnow().isoformat(),
                "task_id": str(task_id),
            }
            try:
                s3_key = storage.upload_file(final_report, filename, metadata)
                final_report += f"\n\n---\n**Archived in MinIO**: `{s3_key}`"
            except Exception as e:
                logger.error(f"[{self.role}] Upload failed: {e}")

        # ------------------------------------------------------------------
        # 6. AUTO-HANDOFF → Router inbox
        #    Fires only in stateful sessions (conversation_id present).
        #    Never blocks or raises — wrapped so a Redis hiccup can't
        #    break the build pipeline.
        # ------------------------------------------------------------------
        if conversation_id:
            try:
                from app.core.agent_memory import write_handoff

                # Extract a clean review grade from the reviewer output
                grade_match = re.search(r"(Pass|Fail)", review, re.IGNORECASE)
                grade = grade_match.group(1).upper() if grade_match else "UNKNOWN"

                handoff_summary = (
                    f"Architect completed build for: '{goal}'. "
                    f"Steps: {len(steps)}. "
                    f"Security grade: {grade}. "
                    f"conversation_id: {conversation_id}."
                    + (f" task_id: {task_id}." if task_id else "")
                )

                write_handoff(
                    to_agent_id="router",
                    from_agent_id="architect",
                    summary=handoff_summary,
                    links=[task_id] if task_id else [],
                )
                logger.info(
                    f"[{self.role}] 📬 Handoff sent to router — "
                    f"grade={grade}, steps={len(steps)}"
                )
            except Exception as exc:
                # Fail silently — handoff is best-effort, never breaks the pipeline
                logger.warning(f"[{self.role}] Auto-handoff failed (non-fatal): {exc}")

        return final_report


# Global Instance
architect = ArchitectAgent()
